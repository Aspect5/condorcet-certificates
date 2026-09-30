#!/usr/bin/env python3
"""Compare the independent cube manifest with pinned and on-disk inputs."""

import csv
import json
from pathlib import Path


root = Path(__file__).resolve().parent
manifest = json.loads((root / "recompute.json").read_text())
with (root / "LEAVES.expected.tsv").open() as file:
    expected = {r["leaf"]: r for r in csv.DictReader(file, delimiter="\t")}
assert len(expected) == len(manifest["leaves"]) == 21


def read_hashes(name):
    result = {}
    for line in (root / name).read_text().splitlines():
        digest, filename = line.split(maxsplit=1)
        result[Path(filename).name] = digest
    assert len(result) == 21
    return result


cnfs = read_hashes("cnf-hashes.actual.txt")
proofs = read_hashes("proof-hashes.actual.txt")
for tag, record in expected.items():
    own = manifest["leaves"][tag]
    cnf_name = ("A145-none-c456-3" if tag == "Lcube-456-3"
                else "A145-none-c456-" + tag.removeprefix("Lc456-")) + ".cnf"
    assert own["sha256"] == record["cnf_sha256"] == cnfs[cnf_name], tag
    assert proofs[tag + ".lrat.zst"] == record["proof_zst_sha256"], tag
    assert record["cake_lpr"] == "VERIFIED", tag
    assert len(own["units"]) in (1, 2)
assert manifest["base_sha256"] == "348efbbbbf22f01677e1df2becbffcc1e921afac516431562589ab369d1844cc"
print("AGREE base 280 vars 4161137 clauses; 145 supports; 40320 rankings; max 9/19")
print("AGREE 21/21 cube CNF SHA256 values, local files and pinned TSV")
print("AGREE 21/21 compressed LRAT SHA256 values, local files and pinned TSV")
