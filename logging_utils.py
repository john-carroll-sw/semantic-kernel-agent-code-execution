def log_message(message):
    COLORS = {"MESSAGE": "\033[95m", "ENDC": "\033[0m"}  # Reset
    print(f"{COLORS['MESSAGE']}{message}{COLORS['ENDC']}")

def log_flow(from_agent, to_agent):
    COLORS = {
        "FROM_AGENT": "\033[94m",  # Blue
        "TO_AGENT": "\033[92m",  # Green
        "ENDC": "\033[0m",  # Reset
    }
    print(
        f"{COLORS['FROM_AGENT']}{from_agent.capitalize()}{COLORS['ENDC']} (to {COLORS['TO_AGENT']}{to_agent.capitalize() or '*'}{COLORS['ENDC']}): \n"
    )

def log_from_agent(from_agent):
    COLORS = {
        "FROM_AGENT": "\033[92m",  # Green
        "ENDC": "\033[0m",  # Reset
    }
    print(f"{COLORS['FROM_AGENT']}{from_agent.capitalize()}{COLORS['ENDC']}: \n")

def log_separator():
    YELLOW = "\033[93m"
    ENDC = "\033[0m"
    print(
        f"{YELLOW}>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>{ENDC}\n"
    )
