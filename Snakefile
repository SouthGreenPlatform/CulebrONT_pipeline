#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from pprint import pprint as pp
from snakemake.logging import logger
from snakemake.dag import DAG
from snakemake.io import load_configfile
import os
# load own functions
from AdditionalScripts.tools import CulebrONT, get_last_version, get_version

# GLOBAL VARIABLES
# recovery basedir where culebront was installed
basedir = workflow.basedir
CULEBRONT_PATH = Path(basedir)

logo = CULEBRONT_PATH.joinpath('SupplementaryFiles/culebront_logo.png').as_posix()

version_CulebrONT = get_version(basedir)

logger.info(f"""
    Welcome to CulebrONT  !
    Created on November 2019
    version: {version_CulebrONT}
    @author: Julie Orjuela (IRD), Aurore Comte (IRD), Sebastien Ravel (CIRAD), Florian Charriat (CIRAD), Bao Tram Vi (IRD), François Sabot (IRD) and Sebastien Cunnac (IRD)
    @email: julie.orjuela@ird.fr, aurore@comte.ird.fr

    #     .-+.
    #   `odNNh
    #   +NNd:
    #  .Nh.   ---:`
    #  -Nm`  ````./
    #   oNm/ ```-o-
    #    .yNmo/+/.     .oooooo.               oooo             .o8                  .oooooo.   ooooo      ooo ooooooooooooo
    #    `-+ydNmo.    d8P'  `Y8b              `888            "888                 d8P'  `Y8b  `888b.     `8' 8'   888   `8
    #  `/s+../oNNN:  888          oooo  oooo   888   .ooooo.   888oooo.  oooo d8b 888      888  8 `88b.    8       888
    #  +s/     `hNm  888          `888  `888   888  d88' `88b  d88' `88b `888""8P 888      888  8   `88b.  8       888
    #  os:  ////hNN` 888           888   888   888  888ooo888  888   888  888     888      888  8     `88b.8       888
    #  -so- .//sNNs  `88b    ooo   888   888   888  888    .o  888   888  888     `88b    d88'  8       `888       888
    #   `/oo:.yNd/    `Y8bood8P'   `V88V"V8P' o888o `Y8bod8P'  `Y8bod8P' d888b     `Y8bood8P'  o8o        `8      o888o
    #     -yooo+.
    #   `yNs.`-/oo:
    #   dNo` ....+s+
    #   :shmdddhhy+:

    Please cite our github https://github.com/SouthGreenPlatform/CulebrONT_pipeline
    Licencied under CeCill-C (http://www.cecill.info/licences/Licence_CeCILL-C_V1-en.html)
    and GPLv3 Intellectual property belongs to IRD and authors.

    {get_last_version(version_CulebrONT)}
    """)

################ CONFIGFILE EXTRACTION ################
# def install_dag_hook(callback):
#     def postprocess_hook(self, __origmeth=DAG.postprocess):
#         __origmeth(self)
#         callback(self)
#     DAG.postprocess = postprocess_hook
#
# def dag_finalized(dag):
#     for j in dag.jobs:
#         print(j.output, j.output_mintime, j.input_maxtime)

### to use on V2
# install_dag_hook(dag_finalized)
# pp(DAG.__dict__)

# importing configuration files
# pp(workflow.__dict__)

# pp(workflow.basedir)

if not workflow.overwrite_configfiles:
    raise ValueError("ERROR CulebrONT: You need to use --configfile option to snakemake command line")
else:
    path_config = workflow.overwrite_configfiles[0]

cluster_config: CULEBRONT_PATH.joinpath("cluster_config.yaml")
tools_config  = load_configfile(CULEBRONT_PATH.joinpath("tools_path.yaml"))



# --- Verification Configuration Files --- #
# using schemas to check mandatory value from yaml format
# print(config)
culebront = CulebrONT(config, path_config, tools_config, CULEBRONT_PATH)
# pp(culebront.export_use_yaml)

# print for debug:
# logger.debug(pp(culebront))
# exit()

# Getting paths on usefully variables
output_dir = config['DATA']['OUTPUT']
fastq_dir = config['DATA']['FASTQ']
reference_file = config['DATA']['REF']

# path_snake = workflow.snakefile
# print(f"path_snake: {path_snake}")

################ WILDCARDS  ################
FASTQ, = glob_wildcards(f"{config['DATA']['FASTQ']}{{fastq}}{culebront.fastq_files_ext}")
nb_racon_rounds = culebront.nb_racon_rounds

# load some variables from culebront class
add_circular_name = culebront.add_circular_name

#output of Minipolish, -> (input de Tag Circular Minipolish)
TMP = culebront.TMP
#output of Tag Circular Minipolish , -> (input de fixstart)
TCM = culebront.TCM
#output of raven, shasta, flye, circlator , -> (input de tag_circular)
TAG = culebront.TAG

#######################################
# Change workdir to output path
workdir:config["DATA"]["OUTPUT"]
#######################################


def get_threads(rule, default):
    """
    give threads or 'cpus-per-task from cluster_config rule : threads to SGE and cpus-per-task to SLURM
    """
    if rule in cluster_config and 'threads' in cluster_config[rule]:
        return int(cluster_config[rule]['threads'])
    elif rule in cluster_config and 'cpus-per-task' in cluster_config[rule]:
        return int(cluster_config[rule]['cpus-per-task'])
    elif '__default__' in cluster_config and 'cpus-per-task' in cluster_config['__default__']:
        return int(cluster_config['__default__']['cpus-per-task'])
    elif '__default__' in cluster_config and 'threads' in cluster_config['__default__']:
        return int(cluster_config['__default__']['threads'])
    return default

def get_fastq(wildcards):
    return f"{fastq_dir}{wildcards.fastq}{culebront.fastq_files_ext}"


def draft_to_circlator(wildcards):
    if 'CANU' in wildcards.assemblers:
        return rules.run_canu.output.fasta
    if 'SMARTDENOVO' in wildcards.assemblers:
        return rules.run_smartdenovo.output.fasta
    else:
        return 'None'

def draft_to_racon(wildcards):
    n = int(wildcards.nb)
    if n == 1:
        if config['CIRCULAR']:
            return f"{output_dir}{{fastq}}/ASSEMBLERS/{{assemblers}}/POLISHING/ROTATE/rotate_{n}/assembly.racon{n}.fasta"
        else:
            return f"{output_dir}{{fastq}}/ASSEMBLERS/{{assemblers}}/ASSEMBLER/assembly{add_circular_name}.fasta"
    elif n > 1:
        if config['CIRCULAR']:
            return f"{output_dir}{{fastq}}/ASSEMBLERS/{{assemblers}}/POLISHING/ROTATE/rotate_{n}/assembly.racon{n}.fasta"
        else:
            return f"{output_dir}{{fastq}}/ASSEMBLERS/{{assemblers}}/POLISHING/RACON/racon_{n-1}/assembly.racon{n-1}.fasta"
    else:
        raise ValueError(f"loop numbers must be 1 or greater: received {n}")

def draft_to_rotate(wildcards):
    n = int(wildcards.nb)
    if n == 1:
        return  f"{output_dir}{{fastq}}/ASSEMBLERS/{{assemblers}}/ASSEMBLER/assemblyCIRCULARISED_circTag.fasta"
    elif n > 1:
        return f"{output_dir}{{fastq}}/ASSEMBLERS/{{assemblers}}/POLISHING/RACON/racon_{n-1}/assembly.racon{n-1}.fasta"
    else:
        raise ValueError(f"loop numbers must be 1 or greater: received {n}")

def draft_to_correction(wildcards):
    if 'MINIASM' == wildcards.assemblers:
        return f"{output_dir}{{fastq}}/ASSEMBLERS/{{assemblers}}/POLISHING/RACON/racon_{nb_racon_rounds}/assembly.racon{nb_racon_rounds}{TCM}.fasta"
    elif config['POLISHING']['RACON']:
        return f"{output_dir}{{fastq}}/ASSEMBLERS/{{assemblers}}/POLISHING/RACON/racon_{nb_racon_rounds}/assembly.racon{nb_racon_rounds}.fasta"
    else:
        return f"{output_dir}{{fastq}}/ASSEMBLERS/{{assemblers}}/ASSEMBLER/assembly{add_circular_name}.fasta"


################################ FINAL ####################################
rule final:
    input:
        f"{output_dir}FINAL_REPORT/CulebrONT_report.html"


################################ ASSEMBLY ####################################
include: f"{basedir}/snakefiles/assemblers.snake"

############################### CIRCULARISATION ##############################
include: f"{basedir}/snakefiles/circular.snake"

################################ POLISHING ####################################
include: f"{basedir}/snakefiles/polishers.snake"

################################ CORRECTION ####################################
include: f"{basedir}/snakefiles/correction.snake"

################################ QUALITY ####################################
include: f"{basedir}/snakefiles/quality.snake"

################################ RAPPORT ####################################

rule rule_graph:
    """
    run dag on {rule}
    """
    threads: get_threads('rule_graph', 1)
    input:
        conf = str(path_config),
    params:
        tmp = f"{output_dir}FINAL_REPORT/dag.tmp"
    output:
        dag = f"{output_dir}FINAL_REPORT/dag.png"
    message:
        """
        making dag ...
        snakemake -n --rulegraph --configfile {input.conf} > {params.tmp}
        dot -Tpng {params.tmp}
        """
    shell:
        """
        cd {basedir}
        snakemake -s {basedir}/Snakefile -n --rulegraph --configfile {input.conf} >{params.tmp}
        dot -Tpng {params.tmp} >{output.dag}
        rm {params.tmp}
        """

rule run_report_snakemake:
    """
    run dag on {rule}
    """
    threads: get_threads('run_report_snakemake', 1)
    input:
        conf = str(path_config),
    output:
        report_snakemake = f"{output_dir}FINAL_REPORT/snake_report.html"
    message:
        """
        making report ...
        snakemake -n --configfile {input.conf} --report {output.report_snakemake}
        """
    # singularity:
        # tools_config['SINGULARITY']['REPORT']
    shell:
        """
        cd {basedir}
        snakemake -s {basedir}/Snakefile --configfile {input.conf} --report {output.report_snakemake}
        """

rule run_busco_stats:
    """
    run stat
    """
    threads: get_threads('run_stats', 1)
    input:
        summary = expand(rules.run_busco.output.summary, fastq='{fastq}', assemblers=culebront.assembly_tools_activated, quality_step=culebront.quality_step)
    output:
        stat = f"{output_dir}{{fastq}}/REPORT/{{fastq}}_busco.csv",
    params:
        quality_list = culebront.quality_step,
        assembly_list = culebront.assembly_tools_activated,
        out_dir = directory(f"{output_dir}{{fastq}}/"),
    priority: 10
    message:
        """
        make stats
        """
    script:
        f"{basedir}/reports/getStats.py"

def get_inputs_benchmark(wildcards):
    dico_benchmark_inputs = {
            "assembly_list": expand(f"{output_dir}{{{{fastq}}}}/BENCHMARK/ASSEMBLER/{{assemblers}}.txt", assemblers=culebront.assembly_tools_activated)
            
        }
    if culebront.polishing_tools_activated:
        dico_benchmark_inputs["polishers_list"] = expand(f"{output_dir}{{{{fastq}}}}/BENCHMARK/POLISHING/{{assemblers}}_{{polishers}}{{nb}}.txt", 
                    assemblers=[ass for ass in culebront.assembly_tools_activated if ass not in ["MINIASM"]], 
                    polishers=culebront.polishing_tools_activated,
                    nb = range(1, int(nb_racon_rounds)+1))

    if culebront.correction_tools_activated:
        dico_benchmark_inputs["correction_list"] = expand(f"{output_dir}{{{{fastq}}}}/BENCHMARK/CORRECTION/{{correction}}/{{assemblers}}.txt", 
                    assemblers=culebront.assembly_tools_activated, 
                    correction=culebront.correction_tools_activated)

    # if culebront.quality_tools_activated:
        # dico_benchmark_inputs["quality_list"] = expand(f"{output_dir}{{{{fastq}}}}/BENCHMARK/POLISHING/{{assemblers}}_{{polishers}}{{nb}}.txt", 
                    # assemblers=culebront.assembly_tools_activated, 
                    # polishers=culebront.polishing_tools_activated,
                    # nb = range(1, int(nb_racon_rounds)+1))
    # pprint.pprint(dico_benchmark_inputs)
    return dico_benchmark_inputs


rule run_benchmark_time:
    """
    run benchmark
    """
    threads: get_threads('run_benchmark_time', 1)
    input:
        unpack(get_inputs_benchmark)
    output:
        stat_time = f"{output_dir}{{fastq}}/REPORT/{{fastq}}_time.csv",
    params:
        out_dir = f"{output_dir}{{fastq}}",
        sample = f"{{fastq}}",
        dico = get_inputs_benchmark
    message:
        """
        unpacking final dico and benchmark
        """
    # singularity:
        # tools_config['SINGULARITY']['REPORT']
    script:
        f"{basedir}/reports/getBenchmark.py"

def output_final(wildcards):
    dico_final = {
        "fasta_list" : expand(rules.preparing_fasta_to_quality.output.renamed, fastq=FASTQ, assemblers=culebront.assembly_tools_activated, quality_step=culebront.quality_step),
        "dag" : rules.rule_graph.output.dag,
        "bench_list" : expand(rules.run_benchmark_time.output.stat_time,fastq=FASTQ),
        # "report_snakemake" : rules.run_report_snakemake.output.report_snakemake,
        }
    if config['QUALITY']['QUAST']:
        dico_final.update({
            "quast_files": expand(rules.run_quast.output.report_file, fastq=FASTQ)
         })
    if config['QUALITY']['BUSCO']:
         dico_final.update({
         "busco_stats": expand(rules.run_busco_stats.output.stat, fastq = FASTQ),
         })
    if config['QUALITY']['BLOBTOOLS']:
        dico_final.update({
            "blob_files": expand(rules.run_blobtools.output.table, fastq=FASTQ, assemblers=culebront.assembly_tools_activated, quality_step=culebront.last_steps_list)
        })
    if config['QUALITY']['WEESAM']:
        dico_final.update({
             "weesam_dirs": expand(rules.run_weesam.output.txt, fastq=FASTQ, assemblers=culebront.assembly_tools_activated, quality_step=culebront.last_steps_list)
        })
    if config['QUALITY']['ASSEMBLYTICS']:
        dico_final.update({
             "assemblytics_files": expand(rules.run_assemblytics.output.summary, fastq=FASTQ, assemblers=culebront.assembly_tools_activated, quality_step=culebront.last_steps_list)
        })
    if config['QUALITY']['KAT']:
        dico_final.update({
            "kat_files":  expand(rules.run_KAT.output.gcp, fastq=FASTQ, assemblers=culebront.assembly_tools_activated, quality_step=culebront.last_steps_list)
        })
    if config['MSA']['MAUVE']:
        dico_final.update({
            "mauve_files": expand(f"{output_dir}{{fastq}}/AGGREGATED_QC/MAUVE_ALIGN/candidate_assemblies.xmfa", fastq=FASTQ)
        })
    return dico_final


rule run_report:
    """
    printing  CulebrONT report
    """
    threads: get_threads('run_report', 1)
    input:
        unpack(output_final)
    params:
        samples_list = FASTQ,
        txt_config = culebront.export_use_yaml,
        out_dir_report = directory(f"{output_dir}FINAL_REPORT"),
        quality_tools_list = culebront.quality_tools_activated,
        logo = logo
    output:
        report = f"{output_dir}FINAL_REPORT/CulebrONT_report.html"
    message:
        """
        print final CulebrONT_report ...
        """
    singularity:
        tools_config['SINGULARITY']['REPORT']
    script:
        f"{basedir}/reports/Report.Rmd"
