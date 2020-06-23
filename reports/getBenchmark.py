import re
import pandas as pd
import csv

fastq = snakemake.input.fastq
m = re.search(r'\/([\w-]+)\.f[\w\.]+$', fastq)
if m:
    fq = m.group(1)
assemblers = snakemake.params.liste_assemblers
steps = snakemake.params.liste_busco
out_repository = snakemake.params.out_dir
correcters = snakemake.params.liste_correcteurs
racon_round = snakemake.params.racon_round
if snakemake.params.medaka_training == True:
    medaka_steps = ["TRAIN","CONSENSUS"]
else:
    medaka_steps = ["CONSENSUS"]

results_time = {}
for step in steps:
    for assembler in assemblers:
        if step == "STEP_ASSEMBLY":
            with open(f"{out_repository}/LOGS/ASSEMBLER/{assembler}/{fq}_{assembler}-BENCHMARK.txt", 'r') as f:
                spamreader = csv.reader(f, delimiter = "\t")
                for line in spamreader:
                    if re.match(r"^\d",line[0]):
                        results_time[assembler, "ASSEMBLER"] = line[0]
        elif step == "STEP_POLISHING_RACON":
                for i in range(1,racon_round+1):
                    with open(f"{out_repository}/LOGS/POLISHING/RACON/{fq}_{assembler}_RACON{i}-BENCHMARK.txt", 'r') as f:
                        spamreader = csv.reader(f, delimiter="\t")
                        for line in spamreader:
                            if re.match(r"^\d", line[0]):
                                results_time[assembler, f"RACON{i}"] = [line[0]]
        elif step == "STEP_CORRECTION_NANOPOLISH":
            with open(f"{out_repository}/LOGS/CORRECTION/NANOPOLISH/{fq}_{assembler}_NANOPOLISH-BENCHMARK.txt", 'r') as f:
                spamreader = csv.reader(f, delimiter="\t")
                for line in spamreader:
                    if re.match(r"^\d", line[0]):
                        results_time[assembler, "NANOPOLISH"] = [line[0]]
        elif step == "STEP_CORRECTION_MEDAKA":
            for medaka_step in medaka_steps:
                with open(f"{out_repository}/LOGS/CORRECTION/MEDAKA/{fq}_{assembler}_MEDAKA_{medaka_step}-BENCHMARK.txt", 'r') as f:
                    spamreader = csv.reader(f, delimiter="\t")
                    for line in spamreader:
                        if re.match(r"^\d", line[0]):
                            results_time[assembler, f"MEDAKA_{medaka_step}"] = [line[0]]

df = pd.DataFrame(results_time)
df.to_csv(snakemake.output.stat)