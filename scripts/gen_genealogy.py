#!/usr/bin/env python
import os
import json
import argparse


def build_mapping(root_dir: str) -> dict:
    """
    root_dir 아래에 있는 source/idx/filename 구조를 순회해서
    filename -> {"source": source, "idx": idx} 매핑을 만든다.
    """
    mapping = {}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, root_dir)
            parts = rel_path.split(os.sep)

            # 최소한 source/idx/filename 구조를 만족해야 함
            if len(parts) < 3:
                continue

            source = parts[-3]
            idx = parts[-2]

            # filename 을 key 로 사용
            if filename in mapping:
                # 같은 파일명이 여러 군데 있을 수 있으면,
                # 여기서 로깅하거나, 리스트로 누적하는 식으로 바꿔도 됨.
                # 지금은 그냥 덮어씀.
                pass

            mapping[filename] = {
                "source": source,
                "idx": idx,
            }

    return mapping


def main():
    parser = argparse.ArgumentParser(
        description="source/idx/filename 구조에서 filename -> {source, idx} JSON 생성"
    )
    parser.add_argument(
        "--root_dir",
        default="./dataset",
        help="source/idx/filename 구조가 있는 루트 디렉토리",
    )
    parser.add_argument(
        "--output_json",
        default="./backend/genealogy.json",
        help="결과를 저장할 JSON 파일 경로",
    )
    args = parser.parse_args()

    mapping = build_mapping(args.root_dir)

    os.makedirs(os.path.dirname(os.path.abspath(args.output_json)), exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"Saved mapping for {len(mapping)} files to {args.output_json}")


if __name__ == "__main__":
    main()
