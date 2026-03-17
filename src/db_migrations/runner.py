from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, MetaData, String, Table, Text, func, select
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MigrationFile:
    version: str
    description: str
    name: str
    path: Path
    checksum: str
    sql: str


class MigrationRunner:
    """A minimal Flyway-style SQL migration runner."""

    def __init__(self, engine: Engine, metadata) -> None:
        self.engine = engine
        self.metadata = metadata
        self.migrations_dir = Path(__file__).resolve().parent / "sql"
        self.history_metadata = MetaData()
        self.history_table = Table(
            "schema_migrations",
            self.history_metadata,
            Column("version", String(64), primary_key=True),
            Column("description", String(255), nullable=False),
            Column("script", String(255), nullable=False),
            Column("checksum", String(32), nullable=False),
            Column("installed_by", String(128), nullable=False, default="dsa"),
            Column("installed_on", DateTime, nullable=False, server_default=func.now()),
            Column("execution_time_ms", String(32), nullable=False),
            Column("success", Boolean, nullable=False, default=True),
            Column("notes", Text),
        )

    def migrate(self) -> None:
        self.history_metadata.create_all(self.engine, checkfirst=True)
        migrations = self._load_migrations()
        applied = self._load_applied_migrations()
        self._validate_applied_migrations(migrations, applied)

        pending = [migration for migration in migrations if migration.version not in applied]
        for migration in pending:
            self._apply_migration(migration)

        if pending:
            logger.info("数据库迁移完成，共执行 %s 个 migration", len(pending))
        else:
            logger.info("数据库迁移已是最新，无需执行 migration")

    def _load_applied_migrations(self) -> dict:
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(
                    self.history_table.c.version,
                    self.history_table.c.script,
                    self.history_table.c.checksum,
                    self.history_table.c.success,
                )
            ).all()
        return {
            row.version: {
                "script": row.script,
                "checksum": row.checksum,
                "success": row.success,
            }
            for row in rows
        }

    def _load_migrations(self) -> List[MigrationFile]:
        if not self.migrations_dir.exists():
            return []

        selected: dict[str, dict] = {}
        current_dialect = self.engine.dialect.name
        for path in sorted(self.migrations_dir.glob("V*.sql")):
            parsed = self._parse_migration_filename(path)
            if parsed["dialect"] not in (None, current_dialect):
                continue
            current = selected.get(parsed["version"])
            if current is None or (parsed["dialect"] == current_dialect and current["dialect"] is None):
                selected[parsed["version"]] = parsed

        migrations: List[MigrationFile] = []
        for version in sorted(selected):
            parsed = selected[version]
            sql = parsed["path"].read_text(encoding="utf-8")
            migrations.append(
                MigrationFile(
                    version=parsed["version"],
                    description=parsed["description"],
                    name=parsed["path"].name,
                    path=parsed["path"],
                    checksum=hashlib.md5(sql.encode("utf-8")).hexdigest(),
                    sql=sql,
                )
            )
        return migrations

    def _parse_migration_filename(self, path: Path) -> dict:
        stem = path.name[:-4]
        dialect: Optional[str] = None
        for candidate in (self.engine.dialect.name, "mysql", "sqlite"):
            suffix = f".{candidate}"
            if stem.endswith(suffix):
                dialect = candidate
                stem = stem[: -len(suffix)]
                break

        if "__" not in stem:
            raise RuntimeError(f"Invalid migration filename: {path.name}")

        version_part, description_part = stem.split("__", 1)
        return {
            "version": version_part[1:],
            "description": description_part.replace("_", " "),
            "path": path,
            "dialect": dialect,
        }

    def _validate_applied_migrations(self, migrations: List[MigrationFile], applied: dict) -> None:
        available = {migration.version: migration for migration in migrations}
        for version, record in applied.items():
            if not record["success"]:
                raise RuntimeError(f"Migration {version} is marked failed in schema_migrations")
            migration = available.get(version)
            if migration is None:
                logger.warning("Applied migration %s not found in codebase", version)
                continue
            if migration.checksum != record["checksum"]:
                if self._is_legacy_python_migration(record["script"], migration.name):
                    self._upgrade_legacy_history_record(version, migration)
                    continue
                raise RuntimeError(
                    f"Migration checksum mismatch for version {version}: "
                    f"db={record['checksum']} code={migration.checksum}"
                )

    def _apply_migration(self, migration: MigrationFile) -> None:
        logger.info("执行 migration %s - %s", migration.version, migration.description)
        start = perf_counter()
        with self.engine.begin() as conn:
            for statement in self._split_sql_statements(migration.sql):
                conn.exec_driver_sql(statement)
            elapsed_ms = int((perf_counter() - start) * 1000)
            conn.execute(
                self.history_table.insert().values(
                    version=migration.version,
                    description=migration.description,
                    script=migration.name,
                    checksum=migration.checksum,
                    installed_by="dsa",
                    execution_time_ms=str(elapsed_ms),
                    success=True,
                    notes=None,
                )
            )

    def _split_sql_statements(self, sql: str) -> List[str]:
        statements: List[str] = []
        current: List[str] = []
        in_single = False
        in_double = False
        in_line_comment = False
        in_block_comment = False
        i = 0

        while i < len(sql):
            ch = sql[i]
            nxt = sql[i + 1] if i + 1 < len(sql) else ""

            if in_line_comment:
                current.append(ch)
                if ch == "\n":
                    in_line_comment = False
                i += 1
                continue

            if in_block_comment:
                current.append(ch)
                if ch == "*" and nxt == "/":
                    current.append(nxt)
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            if not in_single and not in_double:
                if ch == "-" and nxt == "-":
                    in_line_comment = True
                    current.append(ch)
                    current.append(nxt)
                    i += 2
                    continue
                if ch == "/" and nxt == "*":
                    in_block_comment = True
                    current.append(ch)
                    current.append(nxt)
                    i += 2
                    continue

            if ch == "'" and not in_double:
                in_single = not in_single
                current.append(ch)
                i += 1
                continue

            if ch == '"' and not in_single:
                in_double = not in_double
                current.append(ch)
                i += 1
                continue

            if ch == ";" and not in_single and not in_double:
                statement = "".join(current).strip()
                if statement:
                    statements.append(statement)
                current = []
                i += 1
                continue

            current.append(ch)
            i += 1

        tail = "".join(current).strip()
        if tail:
            statements.append(tail)
        return statements

    @staticmethod
    def _is_legacy_python_migration(installed_script: str, current_script: str) -> bool:
        return bool(installed_script and installed_script.endswith(".py") and current_script.endswith(".sql"))

    def _upgrade_legacy_history_record(self, version: str, migration: MigrationFile) -> None:
        logger.info("检测到旧版 Python migration 记录，升级历史元数据: %s -> %s", version, migration.name)
        with self.engine.begin() as conn:
            conn.execute(
                self.history_table.update()
                .where(self.history_table.c.version == version)
                .values(script=migration.name, checksum=migration.checksum, notes="upgraded from legacy python migration")
            )
