#!/usr/bin/env python
"""初始化长期记忆集合：清空并重建 Chroma 中的 user_memory 集合。"""

from __future__ import annotations

import argparse
import os
import sys

import chromadb

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.path_tool import get_abs_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clear and recreate the long-term memory collection.",
    )
    parser.add_argument(
        "--persist-directory",
        default="chroma_db",
        help="Chroma persist directory relative to project root.",
    )
    parser.add_argument(
        "--collection-name",
        default="user_memory",
        help="Chroma collection name for long-term memory.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    return parser.parse_args()


def init_long_term_memory(*, persist_directory: str, collection_name: str) -> tuple[int, int]:
    client = chromadb.PersistentClient(path=get_abs_path(persist_directory))

    existing_count = 0
    try:
        collection = client.get_collection(collection_name)
        existing_count = collection.count()
        client.delete_collection(collection_name)
    except Exception:
        existing_count = 0

    recreated = client.get_or_create_collection(collection_name)
    return existing_count, recreated.count()


def main() -> int:
    args = parse_args()

    if not args.yes:
        prompt = (
            f"即将初始化长期记忆集合 {args.collection_name}，"
            "这会删除全部已保存的业务长期记忆。继续请输入 YES: "
        )
        confirmed = input(prompt).strip()
        if confirmed != "YES":
            print("已取消，未做任何修改。")
            return 1

    before_count, after_count = init_long_term_memory(
        persist_directory=args.persist_directory,
        collection_name=args.collection_name,
    )
    print(
        f"长期记忆初始化完成: collection={args.collection_name}, "
        f"deleted={before_count}, current={after_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())