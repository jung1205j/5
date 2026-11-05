from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import pytest
from frontend.data_io import load_dataset, exposed_until, DataContractError, read_results

ROOT = Path(__file__).resolve().parents[1]

def test_demo_contract():
    ds = load_dataset(ROOT / "data" / "demo")
    assert len(ds["persons"]) > 20
    assert len(ds["reactions"]) == 20
    assert len(ds["results"]) == 3
    for r in ds["results"]:
        cumulative, latest = exposed_until(r["steps"], len(r["steps"])-1)
        assert len(cumulative) >= len(latest)
        assert cumulative.issubset(set(ds["persons"]["id"]))

def test_no_initial_exposures():
    assert exposed_until([[1,2], [3]], -1) == (set(), set())
    assert exposed_until([[1,2], [3]], 1) == ({1,2,3}, {3})

def test_missing_folder():
    with pytest.raises(DataContractError):
        load_dataset(ROOT / "data" / "nonexistent")
