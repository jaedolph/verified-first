"""Copy the prod database into this instance's database, replacing everything in it.

The schema is created from the current models, then every column prod also has is copied across, so
prod can be on an older schema (columns it doesn't have yet are left empty, and tables it doesn't
have are skipped). Prod is only read from.

Broadcaster tokens, reward ids and eventsub ids are blanked, so the test instance can't act on real
channels. Re-authorize a channel through the test extension's config page to use it on test.

Requires the PROD_DB_URI env var, e.g. postgresql://postgres:<password>@verifiedfirst-postgres

Usage:
    python -m scripts.copy_prod_to_test
"""

import logging
import os

from sqlalchemy import MetaData, create_engine, insert, select

from verifiedfirst import create_app
from verifiedfirst.database import db

logger = logging.getLogger(__name__)


def copy(prod_db_uri: str) -> None:
    """Replace this instance's database with a copy of prod's.

    :param prod_db_uri: SQLAlchemy URI of the prod database
    """
    prod = create_engine(prod_db_uri)
    prod_meta = MetaData()
    prod_meta.reflect(prod)

    # create_app() registers the models, so this creates the current schema
    db.drop_all()
    db.create_all()
    with prod.connect() as src, db.engine.begin() as dest:
        # sorted_tables puts twitch_user before first, which references it
        for table in db.metadata.sorted_tables:
            prod_table = prod_meta.tables.get(table.name)
            if prod_table is None:
                logger.info("'%s' table is not in prod, skipping.", table.name)
                continue
            columns = [col.name for col in table.columns if col.name in prod_table.c]
            query = select(*(prod_table.c[col] for col in columns))
            rows = [dict(row) for row in src.execute(query).mappings()]
            if table.name == "broadcaster":
                for row in rows:
                    row.update(access_token="", refresh_token="", reward_id=None, eventsub_id=None)
            if rows:
                dest.execute(insert(table), rows)
            logger.info("Copied %d rows into '%s' table.", len(rows), table.name)


def main() -> None:
    """Entry point."""
    logging.getLogger().setLevel(logging.INFO)
    with create_app().app_context():
        copy(os.environ["PROD_DB_URI"])


if __name__ == "__main__":
    main()
