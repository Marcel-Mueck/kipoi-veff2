import click

import pandas as pd


@click.command()
@click.argument(
    "input_tsvs",
    nargs=-1,
    type=click.Path(exists=True, readable=True),
    required=True,
)
@click.argument("merged_tsv", nargs=1, type=click.Path(), required=True)
def merge(input_tsvs, merged_tsv) -> None:
    """Merge multiple tsvs into a single tsvs"""
    index_columns = ["#CHROM", "POS", "ID", "REF", "ALT"]
    dfs = [
        pd.read_csv(input_tsv, sep="\t", index_col=index_columns)
        for input_tsv in input_tsvs
    ]
    df_merged = pd.concat(dfs, axis=1)
    df_merged.to_csv(merged_tsv, sep="\t")


if __name__ == "__main__":
    merge()
