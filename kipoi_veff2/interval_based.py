import csv
from pathlib import Path
from typing import Any, Callable, Dict, Union, List

from dataclasses import dataclass
import numpy as np
import kipoi

MODEL_GROUPS = ["MMSplice"]


@dataclass
class ModelConfig:
    """This generic class describes the configurations for
    models who already have a dataloader that can use vcf/fasta/gtf files
    dircetly and the prediction is a scored effect. Additional dictionary
    is required to map the input parameters of kipoi_veff2 to the input
    parameters of the dataloader. Additionally, a funciton must also be
    provided to extract the variant information from the dataloader
    output"""

    model: str
    cli_to_dataloader_parameter_map: Dict[str, str]
    get_variant_info: Callable[[Dict[str, Any]], Dict[str, str]]

    def get_column_labels(self) -> List:
        """This function produces the header of the output tsv. The first
        five columns comprises of the information about the variant namely
        #CHROM, POS, ID, REF, ALT. The rest of the column headers are
        annotations from the model's description yaml in kipoi if
        available. Otherwise, we use numerics in increasing order
        starting from 1.

        Raises:
            IOError: If the model description is invalid
        """
        self.model_description = kipoi.get_model_descr(self.model)
        targets = self.model_description.schema.targets
        column_labels = targets.column_labels
        target_shape = targets.shape[0]
        variant_column_labels = ["#CHROM", "POS", "ID", "REF", "ALT"]
        if column_labels:
            if len(column_labels) == target_shape:
                return variant_column_labels + [
                    f"{self.model}/{c}" for c in column_labels
                ]
            else:
                raise IOError(
                    "Something wrong with the model description - \
                        length of column names does not match target shape"
                )
        else:
            return variant_column_labels + [
                f"{self.model}/{num+1}" for num in range(target_shape)
            ]

    def get_dataloader(self, cli_params: Dict[str, str]) -> Any:
        """This function returns an dataloader instance initialized
        with the input vcf, fasta and gtf files.

        Raises:
            IOError: If the cli_to_dataloader_parameter_map dict of the
            model configuration does not exactly match the expected input
            parameters of the dataloader
        """
        self.kipoi_model_with_dataloader = kipoi.get_model(
            self.model, source="kipoi", with_dataloader=True
        )
        dataloader_args = {}
        if sorted(cli_params.keys()) != sorted(
            self.cli_to_dataloader_parameter_map.keys()
        ):
            raise IOError(
                "The dataloader is missing one or more required arguments"
            )
        for (
            cli_param_name,
            dataloader_param_name,
        ) in self.cli_to_dataloader_parameter_map.items():
            dataloader_args[dataloader_param_name] = cli_params[cli_param_name]
        return self.kipoi_model_with_dataloader.default_dataloader(
            **dataloader_args
        )


INTERVAL_BASED_MODEL_CONFIGS = {
    "MMSplice/modularPredictions": ModelConfig(
        model="MMSplice/modularPredictions",
        cli_to_dataloader_parameter_map={
            "gtf_file": "gtf",
            "vcf_file": "vcf_file",
            "fasta_file": "fasta_file",
        },
        get_variant_info=lambda batch, index: {
            "chrom": batch["metadata"]["variant"]["chrom"][index],
            "pos": batch["metadata"]["variant"]["pos"][index],
            "id": (
                f'{batch["metadata"]["variant"]["annotation"][index]}'
                f':{batch["metadata"]["exon"]["exon_id"][index]}'
            ),
            "ref": batch["metadata"]["variant"]["ref"][index],
            "alt": batch["metadata"]["variant"]["alt"][index],
        },
    ),
    "MMSplice/deltaLogitPSI": ModelConfig(
        model="MMSplice/deltaLogitPSI",
        cli_to_dataloader_parameter_map={
            "gtf_file": "gtf",
            "vcf_file": "vcf_file",
            "fasta_file": "fasta_file",
        },
        get_variant_info=lambda batch, index: {
            "chrom": batch["metadata"]["variant"]["chrom"][index],
            "pos": batch["metadata"]["variant"]["pos"][index],
            "id": (
                f'{batch["metadata"]["variant"]["annotation"][index]}'
                f':{batch["metadata"]["exon"]["exon_id"][index]}'
            ),
            "ref": batch["metadata"]["variant"]["ref"][index],
            "alt": batch["metadata"]["variant"]["alt"][index],
        },
    ),
    "MMSplice/splicingEfficiency": ModelConfig(
        model="MMSplice/splicingEfficiency",
        cli_to_dataloader_parameter_map={
            "gtf_file": "gtf",
            "vcf_file": "vcf_file",
            "fasta_file": "fasta_file",
        },
        get_variant_info=lambda batch, index: {
            "chrom": batch["metadata"]["variant"]["chrom"][index],
            "pos": batch["metadata"]["variant"]["pos"][index],
            "id": (
                f'{batch["metadata"]["variant"]["annotation"][index]}'
                f':{batch["metadata"]["exon"]["exon_id"][index]}'
            ),
            "ref": batch["metadata"]["variant"]["ref"][index],
            "alt": batch["metadata"]["variant"]["alt"][index],
        },
    ),
    "MMSplice/mtsplice": ModelConfig(
        model="MMSplice/mtsplice",
        cli_to_dataloader_parameter_map={
            "gtf_file": "gtf",
            "vcf_file": "vcf_file",
            "fasta_file": "fasta_file",
        },
        get_variant_info=lambda batch, index: {
            "chrom": batch["metadata"]["variant"]["chrom"][index],
            "pos": batch["metadata"]["variant"]["pos"][index],
            "id": (
                f'{batch["metadata"]["variant"]["annotation"][index]}'
                f':{batch["metadata"]["exon"]["exon_id"][index]}'
            ),
            "ref": batch["metadata"]["variant"]["ref"][index],
            "alt": batch["metadata"]["variant"]["alt"][index],
        },
    ),
    "MMSplice/pathogenicity": ModelConfig(
        model="MMSplice/pathogenicity",
        cli_to_dataloader_parameter_map={
            "gtf_file": "gtf",
            "vcf_file": "vcf_file",
            "fasta_file": "fasta_file",
        },
        get_variant_info=lambda batch, index: {
            "chrom": batch["metadata"]["variant"]["chrom"][index],
            "pos": batch["metadata"]["variant"]["pos"][index],
            "id": f"""{batch["metadata"]["variant"]["annotation"][index]}
            :{batch["metadata"]["exon"]["exon_id"][index]}""",
            "ref": batch["metadata"]["variant"]["ref"][index],
            "alt": batch["metadata"]["variant"]["alt"][index],
        },
    ),
}


def score_variants(
    model_config: ModelConfig,
    vcf_file: Union[str, Path],
    fasta_file: Union[str, Path],
    gtf_file: Union[str, Path],
    output_file: Union[str, Path],
) -> None:
    """This function scores variants. The steps are as follows
    1. A dataloader object is instantiated with the input files
    2. With a default batch size of 32, a scored effect is
    predicted in batches
    3. Variant information is extracted from the data in batches
    4. Scored effects along with variant information is written
    to the tsv file."""
    dataloader = model_config.get_dataloader(
        {
            "fasta_file": fasta_file,
            "gtf_file": gtf_file,
            "vcf_file": vcf_file,
        }
    )
    with open(output_file, "w") as output_tsv:
        tsv_writer = csv.writer(output_tsv, delimiter="\t")
        tsv_writer.writerow(model_config.get_column_labels())
        for batch in dataloader.batch_iter():
            predictions = (
                model_config.kipoi_model_with_dataloader.predict_on_batch(
                    batch["inputs"]
                )
            )

            if not np.isscalar(predictions) and not isinstance(
                predictions, np.ndarray
            ):
                raise ValueError(
                    "Only predictions of type scalar or \
                        numpy.ndarray are supported"
                )

            if np.isscalar(predictions):
                predictions = [predictions]
            for index, pred in enumerate(predictions):
                pred = [pred] if np.isscalar(pred) else list(pred)
                variant_info = model_config.get_variant_info(batch, index)
                tsv_writer.writerow(
                    [
                        variant_info["chrom"],
                        variant_info["pos"],
                        variant_info["id"],
                        variant_info["ref"],
                        variant_info["alt"],
                    ]
                    + pred
                )
