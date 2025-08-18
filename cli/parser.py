import argparse
import os
from colorama import Fore
from Athena.cli.style import DEFAULT_STYLE
from Athena.common.types import (
    InputTypes,
    OutputTypes,
    SetupData
)

parser = argparse.ArgumentParser(
    prog="Athena CLI tool",
    description="Parser for CLI tool"
)
arguments = argparse.Namespace()

def setup_parser():
    parser.add_argument(
        "input",
        type=str,
        help="The input file fed to the Vector database"
    )
    parser.add_argument(
        "schema",
        type=str,
        help="The schema file fed to OpenAI API pipeline for structured outputs."
    )
    parser.add_argument(
        "input_type",
        type=str,
        help="Type of input data"
    )
    parser.add_argument(
        "output_type",
        type=str,
        help="Type of output text"
    )
    parser.add_argument(
        "--debug",
        type=bool,
        default=False,
        help="Enabling/Disabling DEBUG info when using CLI tool"
    )
    global arguments
    arguments = parser.parse_args()

def check_input() -> tuple[bool, str]:
    if not arguments.input_type in InputTypes._member_names_ or not arguments.output_type in OutputTypes._member_names_:
        return False, "Invalid input or output type. Please use one of the following: " + \
                f"InputTypes: {InputTypes._member_names_}, OutputTypes: {OutputTypes._member_names_}"
    
    if not os.path.exists(arguments.input):
        return False, "Input file does not exist."
    
    if (not os.path.exists(arguments.schema)) and arguments.output_type == OutputTypes.JSON.name:
        return False, "Schema path does not exist."
    return True, "Successfully loaded CLI arguments."

def check_arguments() -> None:
    is_valid, message = check_input()
    if not is_valid:
        raise BaseException(message)
    else:
        print(DEFAULT_STYLE.main_color + message + Fore.RESET)

def get_setup_data() -> SetupData:
    check_arguments()
    return SetupData(
        input_type=InputTypes.__getitem__(arguments.input_type),
        output_type=OutputTypes.__getitem__(arguments.output_type),
        input_file=arguments.input,
        schema_file=arguments.schema
    )

setup_parser()