import os
import pytest
import shutil
import subprocess as sp
import sys
import tempfile


@pytest.fixture
def setup():
    temp_dir = tempfile.mkdtemp()

    reads_fp = os.path.abspath(".tests/data/reads/")
    hosts_fp = os.path.abspath(".tests/data/hosts/")
    db_fp = os.path.abspath(".tests/data/db/")

    project_dir = os.path.join(temp_dir, "project/")

    sp.check_output(["sunbeam", "init", "--data_fp", reads_fp, project_dir])

    config_fp = os.path.join(project_dir, "sunbeam_config.yml")

    config_str = f"sbx_kraken: {{kraken_db_fp: {db_fp}}}"
    sp.check_output(
        [
            "sunbeam",
            "config",
            "modify",
            "-i",
            "-s",
            f"{config_str}",
            f"{config_fp}",
        ]
    )

    config_str = f"qc: {{host_fp: {hosts_fp}}}"
    sp.check_output(
        [
            "sunbeam",
            "config",
            "modify",
            "-i",
            "-s",
            f"{config_str}",
            f"{config_fp}",
        ]
    )

    yield temp_dir, project_dir

    shutil.rmtree(temp_dir)


@pytest.fixture
def run_sunbeam(setup):
    temp_dir, project_dir = setup

    output_fp = os.path.join(project_dir, "sunbeam_output")

    try:
        # Run the test job
        sp.check_output(
            [
                "sunbeam",
                "run",
                "--conda-frontend",
                "conda",
                "--profile",
                project_dir,
                "all_classify",
                "--directory",
                temp_dir,
            ]
        )
    except sp.CalledProcessError as e:
        shutil.copytree(os.path.join(output_fp, "logs/"), "logs/")
        shutil.copytree(os.path.join(project_dir, "stats/"), "stats/")
        sys.exit(e)

    shutil.copytree(os.path.join(output_fp, "logs/"), "logs/")
    shutil.copytree(os.path.join(project_dir, "stats/"), "stats/")

    benchmarks_fp = os.path.join(project_dir, "stats/")

    yield output_fp, benchmarks_fp


def test_full_run(run_sunbeam):
    output_fp, benchmarks_fp = run_sunbeam

    all_samples_fp = os.path.join(output_fp, "classify/kraken/all_samples.tsv")

    # Check output
    assert os.path.exists(all_samples_fp)

    with open(all_samples_fp) as f:
        f.readline()
        f.readline()  # Headers
        lines = f.readlines()
        print(lines)
        assert any(
            [
                "2\t0.0\t200.0\tk__Bacteria; p__; c__; o__; f__; g__; s__" in x.strip()
                for x in lines
            ]
        )

    with open(os.path.join(output_fp, "classify/kraken/EMPTY-taxa.tsv")) as f:
        assert (
            f.readline().strip() == "0\t0.0\tk__Bacteria; p__; c__; o__; f__; g__; s__"
        )
