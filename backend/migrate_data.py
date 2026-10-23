"""
CareerLoom AI - MongoDB Atlas Data Migration Script
====================================================
Migrates data from the old database `ai_career_assistant` to `careerloom_ai`.

Collections migrated:
  - users
  - conversations
  - messages
  - sessions (non-expired only)

Safety guarantees:
  - Preserves original _id, timestamps, and password hashes
  - Skips duplicate records (by _id and by email for users)
  - Reports email conflicts without overwriting
  - Never deletes source database
  - Supports --dry-run to preview migration without writes

Usage:
  python -m backend.migrate_data              # Live migration
  python -m backend.migrate_data --dry-run    # Preview only, no writes
  python -m backend.migrate_data --dry-run --verbose
"""

import sys
import argparse
import datetime
from typing import Any, Dict, List

import certifi
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

import os

MONGODB_URI = os.getenv("MONGODB_URI", "")
SOURCE_DB = "ai_career_assistant"
DEST_DB   = "careerloom_ai"

COLLECTIONS = ["users", "conversations", "messages", "sessions"]
SESSION_MAX_AGE_DAYS = 30


def _fmt_id(doc_id) -> str:
    return str(doc_id)


def _safe_email(doc: dict) -> str:
    return str(doc.get("email", "")).strip().lower()


def connect(uri: str) -> MongoClient:
    client = MongoClient(
        uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=8000,
        connectTimeoutMS=8000,
        socketTimeoutMS=8000,
    )
    client.admin.command("ping")
    return client


def count_records(db, collection: str) -> int:
    try:
        return db[collection].estimated_document_count()
    except Exception:
        return 0


def print_db_stats(client: MongoClient, db_name: str, label: str):
    db = client[db_name]
    print(f"\n  [{label}] Database: `{db_name}`")
    for col in COLLECTIONS:
        n = count_records(db, col)
        print(f"    - {col:<16}: {n:>6} documents")


def migrate_users(src_col, dst_col, dry_run: bool, verbose: bool) -> Dict[str, int]:
    stats = {"total": 0, "migrated": 0, "skipped_id": 0, "email_conflict": 0, "errors": 0}
    all_src_users = list(src_col.find({}))
    stats["total"] = len(all_src_users)

    for user in all_src_users:
        user_id = user["_id"]
        email = _safe_email(user)
        try:
            if dst_col.find_one({"_id": user_id}):
                stats["skipped_id"] += 1
                if verbose:
                    print(f"    [SKIP-ID]     user {_fmt_id(user_id)} already exists in destination")
                continue
            existing_email = dst_col.find_one({"email": email})
            if existing_email:
                stats["email_conflict"] += 1
                print(f"    [EMAIL-CONFLICT] email='{email}' already in destination (src_id={_fmt_id(user_id)}, dst_id={_fmt_id(existing_email['_id'])}). Skipping.")
                continue
            if not dry_run:
                dst_col.insert_one(user)
            stats["migrated"] += 1
            if verbose:
                print(f"    [MIGRATED]    user {_fmt_id(user_id)} ({email})")
        except Exception as e:
            stats["errors"] += 1
            print(f"    [ERROR]       user {_fmt_id(user_id)}: {e}")
    return stats


def migrate_generic(src_col, dst_col, collection: str, dry_run: bool, verbose: bool) -> Dict[str, int]:
    stats = {"total": 0, "migrated": 0, "skipped_id": 0, "errors": 0}
    all_docs = list(src_col.find({}))
    stats["total"] = len(all_docs)

    for doc in all_docs:
        doc_id = doc["_id"]
        try:
            if dst_col.find_one({"_id": doc_id}):
                stats["skipped_id"] += 1
                if verbose:
                    print(f"    [SKIP-ID]     {collection} {_fmt_id(doc_id)} already exists")
                continue
            if not dry_run:
                dst_col.insert_one(doc)
            stats["migrated"] += 1
            if verbose:
                print(f"    [MIGRATED]    {collection} {_fmt_id(doc_id)}")
        except Exception as e:
            stats["errors"] += 1
            print(f"    [ERROR]       {collection} {_fmt_id(doc_id)}: {e}")
    return stats


def migrate_sessions(src_col, dst_col, dry_run: bool, verbose: bool) -> Dict[str, int]:
    stats = {"total": 0, "migrated": 0, "skipped_id": 0, "skipped_expired": 0, "errors": 0}
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=SESSION_MAX_AGE_DAYS)
    all_docs = list(src_col.find({}))
    stats["total"] = len(all_docs)

    for doc in all_docs:
        doc_id = doc["_id"]
        created = doc.get("created_at")

        if isinstance(created, datetime.datetime):
            check_dt = created.replace(tzinfo=datetime.timezone.utc) if created.tzinfo is None else created
            if check_dt < cutoff:
                stats["skipped_expired"] += 1
                if verbose:
                    print(f"    [SKIP-EXPIRED] session {_fmt_id(doc_id)} (created: {created})")
                continue
        elif isinstance(created, str):
            try:
                check_dt = datetime.datetime.fromisoformat(created)
                if check_dt.tzinfo is None:
                    check_dt = check_dt.replace(tzinfo=datetime.timezone.utc)
                if check_dt < cutoff:
                    stats["skipped_expired"] += 1
                    continue
            except Exception:
                pass

        try:
            if dst_col.find_one({"_id": doc_id}):
                stats["skipped_id"] += 1
                if verbose:
                    print(f"    [SKIP-ID]     session {_fmt_id(doc_id)} already exists")
                continue
            if not dry_run:
                dst_col.insert_one(doc)
            stats["migrated"] += 1
            if verbose:
                print(f"    [MIGRATED]    session {_fmt_id(doc_id)}")
        except Exception as e:
            stats["errors"] += 1
            print(f"    [ERROR]       session {_fmt_id(doc_id)}: {e}")
    return stats


def run_migration(dry_run: bool = False, verbose: bool = False):
    sep = "=" * 65
    print(sep)
    print("  CareerLoom AI - Data Migration Script")
    print(f"  Source DB  : {SOURCE_DB}")
    print(f"  Dest DB    : {DEST_DB}")
    print(f"  Mode       : {'DRY-RUN (no writes)' if dry_run else 'LIVE MIGRATION'}")
    print(sep)

    if not MONGODB_URI:
        print("\n[FATAL] MONGODB_URI is not set in .env. Aborting.")
        sys.exit(1)

    print("\n[1/6] Connecting to MongoDB Atlas...")
    try:
        client = connect(MONGODB_URI)
        print("  Connected successfully!")
    except Exception as e:
        print(f"  [FATAL] Cannot connect to Atlas: {e}")
        sys.exit(1)

    src_db = client[SOURCE_DB]
    dst_db = client[DEST_DB]

    print("\n[2/6] Current record counts:")
    print_db_stats(client, SOURCE_DB, "SOURCE")
    print_db_stats(client, DEST_DB,   "DEST  ")

    src_collections = src_db.list_collection_names()
    if not src_collections:
        print(f"\n[WARN] Source database '{SOURCE_DB}' has no collections. Nothing to migrate.")
        client.close()
        return

    all_stats: Dict[str, Dict[str, int]] = {}

    print(f"\n[3/6] Migrating collections {'(DRY-RUN)' if dry_run else ''}...")

    print("\n  >> users")
    all_stats["users"] = migrate_users(src_db["users"], dst_db["users"], dry_run=dry_run, verbose=verbose)

    print("\n  >> conversations")
    all_stats["conversations"] = migrate_generic(src_db["conversations"], dst_db["conversations"], "conversations", dry_run=dry_run, verbose=verbose)

    print("\n  >> messages")
    all_stats["messages"] = migrate_generic(src_db["messages"], dst_db["messages"], "messages", dry_run=dry_run, verbose=verbose)

    print("\n  >> sessions")
    all_stats["sessions"] = migrate_sessions(src_db["sessions"], dst_db["sessions"], dry_run=dry_run, verbose=verbose)

    print(f"\n[4/6] Record counts after migration:")
    print_db_stats(client, SOURCE_DB, "SOURCE (unchanged)")
    print_db_stats(client, DEST_DB,   "DEST  (after migration)")

    if not dry_run:
        print("\n[5/6] Ensuring indexes on destination collections...")
        try:
            dst_db["users"].create_index("email", unique=True, background=True)
            dst_db["conversations"].create_index([("user_id", 1), ("updated_at", -1)], background=True)
            dst_db["messages"].create_index([("conversation_id", 1), ("created_at", 1)], background=True)
            dst_db["sessions"].create_index("token", background=True)
            dst_db["sessions"].create_index("user_id", background=True)
            print("  Indexes created/verified.")
        except Exception as e:
            print(f"  [WARN] Index creation error (non-fatal): {e}")
    else:
        print("\n[5/6] Skipping index creation (dry-run).")

    print(f"\n[6/6] Migration Summary {'(DRY-RUN - no changes made)' if dry_run else '(LIVE)'}")
    print(sep)
    total_migrated = 0
    total_errors   = 0

    for col, stats in all_stats.items():
        migrated  = stats.get("migrated", 0)
        skipped   = stats.get("skipped_id", 0)
        email_cnf = stats.get("email_conflict", 0)
        expired   = stats.get("skipped_expired", 0)
        errors    = stats.get("errors", 0)
        total     = stats.get("total", 0)
        total_migrated += migrated
        total_errors   += errors

        line = f"  {col:<16}: total={total:>5}  migrated={migrated:>5}  skipped={skipped:>4}"
        if email_cnf:
            line += f"  email_conflicts={email_cnf}"
        if expired:
            line += f"  expired_skipped={expired}"
        if errors:
            line += f"  ERRORS={errors}"
        print(line)

    print(sep)
    print(f"  TOTAL migrated : {total_migrated}")
    print(f"  TOTAL errors   : {total_errors}")
    if dry_run:
        print("\n  [DRY-RUN] No documents were written. Run without --dry-run to apply.")
    else:
        print(f"\n  [DONE] Source database `{SOURCE_DB}` was NOT deleted.")
        print(f"  [DONE] All data now available in `{DEST_DB}`.")
    print(sep)

    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate CareerLoom AI data from ai_career_assistant to careerloom_ai")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Preview migration without writing any data.")
    parser.add_argument("--verbose", action="store_true", default=False, help="Print every record migrated or skipped.")
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run, verbose=args.verbose)
