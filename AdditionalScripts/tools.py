#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import PosixPath, Path
from snakemake.logging import logger
from snakemake.utils import validate
import yaml
from collections import OrderedDict
import pprint
import re

# GLOBAL VARIABLES
AVAIL_ASSEMBLY = ("CANU", "FLYE", "MINIASM" , "RAVEN",  "SMARTDENOVO" , "SHASTA")
AVAIL_CORRECTION = ("NANOPOLISH", "MEDAKA")
AVAIL_POLISHING = ("RACON")
AVAIL_QUALITY = ("BUSCO", "QUAST", "WEESAM", "BLOBTOOLS", "ASSEMBLYTICS", "KAT")


ALLOW_FASTQ_EXT = (".fastq",".fq",".fq.gz",".fastq.gz")


# DICO_DEPENDENCY_TOOLS = {"ASSEMBLYTICS": ["MUMMER"],
                         # "BLOBTOOLS"   : ["DIAMOND", "MINIMAP2_SAMTOOLS"],
                         # "CIRCULAR"    :["CIRCLATOR"]
                            # }
# CONDA_ENV_KEYS = ("FLYE", "CANU", "MINIPOLISH", "RAVEN", "SMARTDENOVO", "QUAST", \
                  # "BUSCO", "BLOBTOOLS", "KAT", "MAUVE", "MINIASM_MINIMAP2", "RACON_MINIMAP2",\
                  # "NANOPOLISH_MINIMAP2_SAMTOOLS_SEQTK", "MUMMER")
# SINGULARITY_ENV_KEYS = ("REPORT", "SHASTA", "WEESAM", "ASSEMBLYTICS", "MEDAKA")

# def __return_conda_envs_key(self, tool)
    # return list(filter(re.compile(f"^{tool}*").match,CONDA_ENV_KEYS))[0]
    # CIRCLATOR : './envs/circlator.yaml'
        
    # R : './envs/R_for_culebront_cenv.yaml'
    # DIAMOND : './envs/diamond.yaml'
    # MUMMER : './envs/mummer.yaml'
    # MINIMAP2_SAMTOOLS : './envs/minimap2_samtools.yaml'

    # CIRCULAR : True
    # FIXSTART : True


def get_last_version(version_CulebrONT):
    """Function for know the last version of CulebrONT in website

    Arguments:
        version_CulebrONT (str): the actual version of culebrONT

    Returns:
        note: message if new version avail on the website

    Examples:
        >>> mess = get_last_version("1.2.0")
        >>> print(mess)
            Documentation avail at: https://culebront-pipeline.readthedocs.io/en/latest
            NOTE: The Latest version of CulebrONT 1.3.0 is available at https://github.com/SouthGreenPlatform/CulebrONT_pipeline/releases
    """
    try:
        from urllib.request import urlopen
        from re import search
        HTML = urlopen("https://github.com/SouthGreenPlatform/CulebrONT_pipeline/tags").read().decode('utf-8')
        lastRelease = \
        search('/SouthGreenPlatform/CulebrONT_pipeline/releases/tag/.*', HTML).group(0).split("/")[-1].split('"')[0]
        epilogTools = """Documentation avail at: https://culebront-pipeline.readthedocs.io/en/latest/ \n"""
        if version_CulebrONT != lastRelease:
            if lastRelease < version_CulebrONT:
                epilogTools += "\n** NOTE: This CulebrONT version is higher than the production version, you are using a dev version\n"
            elif lastRelease > version_CulebrONT:
                epilogTools += f"\nNOTE: The Latest version of CulebrONT {lastRelease} is available at https://github.com/SouthGreenPlatform/CulebrONT_pipeline/releases\n"
        return epilogTools
    except Exception as e:
        epilogTools = f"\n** ENABLE TO GET LAST VERSION, check internet connection\n{e}\n"
        return epilogTools


def get_version(CULEBRONT):
    """Read VERSION file to know current version

    Arguments:
        CULEBRONT (path): Path to culebront install

    Returns:
        version: actual version read on the VERSION file

    Examples:
        >>> version = get_version("/path/to/install/culebront")
        >>> print(version)
            1.3.0
    """
    with open(Path(CULEBRONT).joinpath("VERSION"), 'r') as version_file:
        return version_file.readline().strip()


def get_dir(path):
    """List of directory include on folder"""
    return [elm.name for elm in Path(path).glob("*") if elm.is_dir()]


def get_files_ext(path, extensions, add_ext=True):
    """List of files with specify extension include on folder

    Arguments:
        path (str): a path to folder
        extensions (list or tuple): a list or tuple of extension like (".py")
        add_ext (bool): if True (default), file have extension
    
    Returns:
        :class:`list`: List of files name with or without extension , with specify extension include on folder
        :class:`list`: List of  all extension found
    
    Examples:
        >>> version = get_version("/path/to/install/culebront")
        >>> print(version)
            1.3.0
     """
    if not (extensions, (list, tuple)) or not extensions:
        raise ValueError(f'ERROR CulebrONT: "extensions" must be a list or tuple not "{type(extensions)}"')
    tmp_all_files = []
    all_files = []
    files_ext = []
    for ext in extensions:
        tmp_all_files.extend(Path(path).glob(f"**/*{ext}"))

    for elm in tmp_all_files:
        ext = "".join(elm.suffixes)
        if ext not in files_ext:
            files_ext.append(ext)
        if add_ext:
            all_files.append(elm.as_posix())
        else:
            if len(elm.suffixes) > 1:

                all_files.append(Path(elm.stem).stem)
            else:
                all_files.append(elm.stem)
    return all_files, files_ext


def convert_genome_size(size): 
    mult = dict(K=10**3, M=10**6, G=10**9, T=10**12, N=1) 
    search = re.search(r'^(\d+\.+\d+)\s*(.*)$', size) 
    if not search or len(search.groups()) != 2: 
        raise ValueError(f"CONFIG FILE CHECKING FAIL : not able to convert genome size please only use int value with{' '.join(mult.keys())} upper or lower, N or empty is bp size") 
    else: 
        value, unit =search.groups() 
        if not unit: 
            return int(value) 
        elif unit and unit.upper() not in mult.keys(): 
            raise ValueError(f"CONFIG FILE CHECKING FAIL : '{unit}' unit value not allow or not able to convert genome size please only use int value with{' '.join(mult.keys())} upper or lower, N or empty is bp size") 
        else: 
            return int(float(value) * mult[unit.upper()])


class CulebrONT(object):
    """
    to read file config
    """
    def __init__(self, config=None, path_config=None, tools_config=None, culebront_path=None):
        self.config = config
        self.tools_config = tools_config
        self.assembly_tools_activated = []
        self.polishing_tools_activated = []
        self.correction_tools_activated = []
        self.quality_tools_activated = []
        self.quality_step = []
        self.last_steps_list = []
        self.pipeline_stop = None

        self.fastq_files_list = []
        self.fastq_files_ext = []
        self.fastq_gzip = None

        self.illumina_files_list = []
        self.illumina_files_ext = []
        self.illumina_gzip = None
        
        self.add_circular_name = None
        self.TMP = None
        self.TCM = None
        self.TAG = None
        
        self.draft_to_correction = None
        self.draft_to_correction_index_fai = None
        self.draft_to_correction_index_mmi = None
        
        self.nb_racon_rounds = None

        self.__check_config_dic(config)
        self.__cleaning_for_rerun()
        try:
            validate(config, culebront_path.joinpath("schemas/config.schema.yaml").resolve().as_posix())
        except Exception as e:
            raise ValueError(f"{e}\n\nCONFIG FILE CHECKING STRUCTURE FAIL : you need to verify {path_config} KEYS:VALUES: {str(e)[30:76]}\n")


    def get_config_value(self, section, key, subsection=None, type_value=None):
        if subsection:
            return self.config[section][subsection][key]
        else:
            return self.config[section][key]

    def set_config_value(self, section, key, value, subsection=None):
        if subsection:
            self.config[section][subsection][key] = value
        else:
            self.config[section][key] = value
    
    @property
    def export_use_yaml(self):
        """Use to print a dump config.yaml with corrected parameters"""

        def represent_dictionary_order(self, dict_data):
            return self.represent_mapping('tag:yaml.org,2002:map', dict_data.items())

        def setup_yaml():
            yaml.add_representer(OrderedDict, represent_dictionary_order)

        setup_yaml()
        return yaml.dump(self.config, default_flow_style=False, sort_keys=False, indent=4)

    def __cleaning_for_rerun(self):
        """Cleaning Report and dags if we rerun the snakemake a second time
        TODO: improve check if final report run maybe check html file"""
        if Path(self.config["DATA"]["OUTPUT"]).joinpath("FINAL_REPORT").exists():
            logger.warning(
                f"\nWARNING: If you want to rerun culebront a second time please delete the {self.config['DATA']['OUTPUT']}FINAL_REPORT and REPORT repertories for each sample\n")

    def __check_dir(self, section, key, mandatory=[], subsection=None ):
        """Check if path is a directory if not empty
            resolve path on config

        Arguments:
            section (str): the first level on config.yaml
            key (str): the final level on config.yaml
            mandatory (list tuple): a list or tuple with tools want mandatory info
            subsection (str): the second level on config.yaml (ie 3 level)
        
        Returns:
            :class:`list`: List of files name with or without extension , with specify extension include on folder
            :class:`list`: List of all extension found
        Raises:
            NotADirectoryError: If config.yaml data `path` does not exist.
        """
        path_value = self.get_config_value(section=section, key=key, subsection=subsection)
        if path_value:
            path = Path(path_value).resolve().as_posix() + "/"
            if (not Path(path).exists() or not Path(path).is_dir()) and key not in ["OUTPUT"]:
                raise NotADirectoryError(f'CONFIG FILE CHECKING FAIL : in the "{section}" section, {f"subsection {subsection}" if subsection else ""}, {key} directory "{path}" {"does not exist" if not Path(path).exists() else "is not a valid directory"}')
            else:
                self.set_config_value(section, key, path, subsection)
        elif len(mandatory) > 0:
            raise NotADirectoryError(f'CONFIG FILE CHECKING FAIL : in the "{section}" section, {f"subsection {subsection}" if subsection else ""}, {key} directory "{path_value}" {"does not exist" if not Path(path_value).exists() else "is not a valid directory"} but is mandatory for tool: {" ".join(mandatory)}')

    def __check_file(self, section, key, mandatory=[], subsection=None):
        """Check if path is a file if not empty
        :return absolute path file"""
        path_value = self.get_config_value(section=section, key=key, subsection=subsection)
        path = Path(path_value).resolve().as_posix()
        if path:
            if not Path(path).exists() or not Path(path).is_file():
                raise FileNotFoundError(f'CONFIG FILE CHECKING FAIL : in the {section} section, {f"subsection {subsection}" if subsection else ""},{key} file "{path}" {"does not exist" if not Path(path).exists() else "is not a valid file"}')
            else:
                self.set_config_value(section, key, path, subsection)
        elif len(mandatory) > 0:
            raise FileNotFoundError(f'CONFIG FILE CHECKING FAIL : in the "{section}" section, {f"subsection {subsection}" if subsection else ""},{key} file "{path_value}" {"does not exist" if not Path(path_value).exists() else "is not a valid file"} but is mandatory for tool: {" ".join(mandatory)}')


    def __check_tools_config(self, section, tool, mandatory=[]):
        """Check if path is a file if not empty
        :return absolute path file"""
        path_file = self.tools_config[section][tool]
        if not re.findall("shub://SouthGreenPlatform/CulebrONT_pipeline",path_file, flags=re.IGNORECASE):
            path = Path(path_file).resolve().as_posix()
            if path:
                if not Path(path).exists() or not Path(path).is_file():
                    raise FileNotFoundError(f'CONFIG FILE CHECKING FAIL : please check tools_config.yaml in the {section} section, {tool} file "{path}" {"does not exist" if not Path(path).exists() else "is not a valid file"}')
                else:
                    self.tools_config[section][tool] = path
            elif len(mandatory) > 0:
                raise FileNotFoundError(f'CONFIG FILE CHECKING FAIL : please check tools_config.yaml in the {section} section, {tool} file "{path}" {"does not exist" if not Path(path_value).exists() else "is not a valid file"} but is mandatory for tool: {" ".join(mandatory)}')


    def __var_2_bool(self, key, tool, to_convert):
        """convert to boolean"""
        if isinstance(type(to_convert), bool): 
            return to_convert
        elif f"{to_convert}".lower() in ("yes", "true", "t"): 
            return True 
        elif f"{to_convert}".lower() in ("no", "false", "f"): 
            return False 
        else: 
            raise TypeError(f'CONFIG FILE CHECKING FAIL : in the "{key}" section, "{tool}" key: "{to_convert}" is not a valide boolean')


    def __build_tools_activated(self, key, allow, mandatory=False):
        tools_activate = []
        for tool, activated in self.config[key].items():
            if tool in allow:
                boolean_activated = self.__var_2_bool(key, tool, activated)
                if boolean_activated:
                    tools_activate.append(tool)
                    self.config[key][tool] = boolean_activated
            else:
                raise ValueError(f'CONFIG FILE CHECKING FAIL : {key} {tool} not allow on CulebrONT"')
        if len(tools_activate) == 0 and mandatory:
            raise ValueError(f"CONFIG FILE CHECKING FAIL : you need to set True for at least one {key} from {allow}")
        return tools_activate

    def __build_quality_step_list(self, only_last=False):
        last_steps_list=[]
        suffix = ""
        if bool(self.config["FIXSTART"]):
            suffix = "_STARTFIXED"
        if self.correction_tools_activated:
            step = "CORRECTION"
            for corrector in self.correction_tools_activated:
                last_steps_list.append(f"STEP_{step}_{corrector}{suffix if step in self.pipeline_stop else ''}" )
            if only_last: 
                return last_steps_list
        
        if self.polishing_tools_activated:
            step = "POLISHING"
            for polisher in self.polishing_tools_activated:
                last_steps_list.append(f"STEP_{step}_{polisher}{suffix if step in self.pipeline_stop else ''}" )
            if only_last: 
                return last_steps_list
        if self.assembly_tools_activated:
            step = "ASSEMBLY"
            last_steps_list.append(f"STEP_{step}{suffix if step in self.pipeline_stop else ''}" )
            # for assembler in self.assembly_tools_activated:
                # last_steps_list.append(f"STEP_{step}_{assembler}{suffix}" )
            if only_last: return last_steps_list
        return last_steps_list

    def __get_last_step(self):
        if self.correction_tools_activated:
            return "CORRECTION"
        if self.polishing_tools_activated:
            return "POLISHING"
        if self.assembly_tools_activated:
            return "ASSEMBLY"

    def __check_config_dic(self, config):
        """Configuration file checking"""
        # check tools activation
        self.assembly_tools_activated = self.__build_tools_activated("ASSEMBLY", AVAIL_ASSEMBLY, True)
        self.polishing_tools_activated = self.__build_tools_activated("POLISHING", AVAIL_POLISHING)
        self.correction_tools_activated = self.__build_tools_activated("CORRECTION", AVAIL_CORRECTION)
        self.quality_tools_activated = self.__build_tools_activated("QUALITY", AVAIL_QUALITY)
        self.pipeline_stop = self.__get_last_step()

        # check mandatory directory
        self.__check_dir(section="DATA",key="OUTPUT")
        self.__check_dir(section="DATA",key="FASTQ", mandatory=self.assembly_tools_activated)

        # check if fastq file for assembly
        self.fastq_files_list, fastq_files_list_ext = get_files_ext(self.get_config_value('DATA','FASTQ'), ALLOW_FASTQ_EXT)
        if not self.fastq_files_list:
            raise ValueError(f"CONFIG FILE CHECKING FAIL : you need to append at least on fastq with extension on {ALLOW_FASTQ_EXT}")
        # check if all fastq have the same extension
        if len(fastq_files_list_ext) > 1:
            raise ValueError(
                f"CONFIG FILE CHECKING FAIL : Please use only the same format for assembly FASTQ data, not: {fastq_files_list_ext}")
        else:
            self.fastq_files_ext = fastq_files_list_ext[0]
        # check if fastq are gzip
        if "gz" in self.fastq_files_ext:
            self.fastq_gzip = True

        ##### CHECK KAT
        if bool(self.config["QUALITY"]["KAT"]):
            self.__check_dir(section="DATA",key="ILLUMINA", mandatory=["KAT"])
            self.illumina_files_list, illumina_files_list_ext = get_files_ext(self.get_config_value('DATA','ILLUMINA'), ALLOW_FASTQ_EXT)
            if not self.illumina_files_list:
                raise ValueError(f"CONFIG FILE CHECKING FAIL : you need to append at least on fastq illumina with extension on {ALLOW_FASTQ_EXT}")
            # check if all fastq have the same extension
            if len(illumina_files_list_ext) > 1:
                raise ValueError(
                    f"CONFIG FILE CHECKING FAIL : Please use only the same format for ILLUMINA FASTQ data, not: {illumina_files_list_ext}")
            else:
                self.illumina_files_ext = illumina_files_list_ext[0]
            # check if fastq are gzip
            if "gz" in self.illumina_files_ext:
                self.illumina_gzip = True

        # build quality_step and last_steps_list; function test if FIXSTART to append only to last step
        self.last_steps_list = self.__build_quality_step_list(only_last=True)
        self.quality_step = self.__build_quality_step_list(only_last=False)

        # check files if QUAST
        if bool(self.config["QUALITY"]["QUAST"]):
            self.__check_file(section="DATA", key="REF")
            genome_pb = convert_genome_size(self.get_config_value('DATA','GENOME_SIZE'))
            self.set_config_value(section="params", subsection="QUAST", key="GENOME_SIZE_PB", value=genome_pb)
        
        # check files if MAUVE
        if bool(self.config["MSA"]["MAUVE"]):
            self.__check_file(section="DATA", key="REF", mandatory=["MAUVE"])
                    # Make sure running Mauve makes sense
            if len(self.assembly_tools_activated) < 2 and len(self.quality_step) < 2:
                raise ValueError("CONFIG FILE CHECKING ERROR : MAUVE is irrelevant if you have a single final assembly as your config file implies (need more than one assembler and/or a correction step). Mauve will not be run !! ")

        # check BUSCO database if activate
        if bool(self.config["QUALITY"]["BUSCO"]):
            self.__check_dir(section='params', subsection='BUSCO', key='DATABASE', mandatory=["BUSCO"] )
            self.__check_tools_config("SINGULARITY","BUSCO", ["BUSCO"])

        # check DIAMOND database if activate
        if bool(self.config["QUALITY"]["BLOBTOOLS"]):
            self.__check_file(section='params', subsection='DIAMOND', key='DATABASE', mandatory=["BLOBTOOLS", 'DIAMOND'] )

        # check if NANOPOLISH activate, if true compare fastq and fast5 files
        if "NANOPOLISH" in self.correction_tools_activated:
            self.__check_dir(section="DATA", key="FAST5", mandatory=["NANOPOLISH"])
            fast5_files_list = get_dir(self.config['DATA']['FAST5'])
            fastq_files_list, _ = get_files_ext(self.config['DATA']['FASTQ'], ALLOW_FASTQ_EXT, add_ext=False)

            if set(fastq_files_list) - set(fast5_files_list):
                raise ValueError(f"CONFIG FILE CHECKING ERROR : You don't have a fast5 repository for each of your fastq file (they should have the same name). This can raise a problem if you choose to use Nanopolish. Please check your data.:\n\t- fast5_files_list:{fast5_files_list}\n\t- fastq_files_list: {fastq_files_list}\n\n")
    
        # check Medaka config if activate
        if bool(self.config['CORRECTION']['MEDAKA']):
            # check singularity image
            self.__check_tools_config("SINGULARITY","MEDAKA")
            if not bool(self.config['params']['MEDAKA']['MEDAKA_TRAIN_WITH_REF']):
                self.__check_file(section='params', subsection='MEDAKA', key='MEDAKA_MODEL_PATH', mandatory=["MEDAKA"])
            else:
                self.__check_file(section='DATA', key='REF', mandatory=["MEDAKA"])

        # Check racon round
        if bool(self.config['POLISHING']['RACON']) and not (0 < int(self.config['params']['RACON']['RACON_ROUNDS']) < 10):
            raise ValueError(f"CONFIG FILE CHECKING ERROR : You have activated RACON, but RACON_ROUNDS is invalid, 0 < RACON_ROUNDS={self.config['params']['RACON']['RACON_ROUNDS']} < 10 . \n")

        ##############################
        # check workflow compatibility
        if not bool(self.config['POLISHING']['RACON']) and bool(self.config['ASSEMBLY']['MINIASM']):
            logger.warning(f"\nWARNING: RACON is automatically launched (2 rounds by default) for minipolish if MINIASM is activated !! . \n")

        # check size of genome
        if int(self.config['params']['QUAST']['GENOME_SIZE_PB']) >= 100000000:
            logger.warning(f"WARNING: CONFIG FILE CHECKING WARNING : Weesam if fixed to FALSE because genome size !! \n")
            self.config['QUALITY']['WEESAM'] = False
        
        # Make sure running fixstart makes sense
        if not bool(self.config['CIRCULAR']) and bool(self.config['FIXSTART']):
            raise ValueError(f"CONFIG FILE CHECKING ERROR : FIXSTART is irrelevant if you have not activated CIRCULAR. FIXSTART will not be run !! \n")

        # if you want run mauve fixstart has to be activated
        if bool(self.config['CIRCULAR']) and not bool(self.config['FIXSTART']):
            raise ValueError(f"CONFIG FILE CHECKING ERROR : FIXSTART must be activated if CIRCULAR is TRUE on config file.  !! \n")


        ###### TODO call __check_tools_config on the function __build_tools_activated
        # check singularity image if SHASTA
        if bool(self.config["ASSEMBLY"]["SHASTA"]):
            self.__check_tools_config("SINGULARITY","SHASTA", ["SHASTA"])
        
        # check singularity image if WEESAM
        if bool(self.config["QUALITY"]["WEESAM"]):
            self.__check_tools_config("SINGULARITY","WEESAM", ["WEESAM"])

        # check singularity image if KAT
        if bool(self.config["QUALITY"]["KAT"]):
            self.__check_tools_config("SINGULARITY","KAT", ["KAT"])
        
        # check singularity image if ASSEMBLYTICS
        if bool(self.config["QUALITY"]["ASSEMBLYTICS"]):
            self.__check_tools_config("SINGULARITY","ASSEMBLYTICS", ["ASSEMBLYTICS"])
        
        # check singularity image for BLOBTOOLS
        if bool(self.config["QUALITY"]["BLOBTOOLS"]):
            self.__check_tools_config("SINGULARITY","BLOBTOOLS",["BLOBTOOLS"])
        
        # check singularity image for Report
        self.__check_tools_config("SINGULARITY","REPORT",["REPORT"])
        
        
        ## TODO CHANGE
        for key in self.tools_config['CONDA']:
            self.__check_tools_config("CONDA",key)        
        
        #############################################
        # Build variables name for files
        if bool(self.config['CIRCULAR']):
            self.add_circular_name = "CIRCULARISED"
            self.TMP = "TMP"
            self.TCM = "FALSE"
        else:
            self.add_circular_name = ""
            self.TMP = ""
            self.TCM = ""
        
        if not bool(self.config['POLISHING']['RACON']) and bool(self.config['CIRCULAR']):
            self.TAG="TMPTAG"
        else:
            self.TAG=""

        # ############################### DEF ####################################
        self.nb_racon_rounds = '2' if not bool(self.config['POLISHING']['RACON']) else str(config['params']['RACON']['RACON_ROUNDS'])


    def __repr__(self):
        return f"{self.__class__}({pprint.pprint(self.__dict__)})"
