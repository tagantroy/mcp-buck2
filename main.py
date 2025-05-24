import subprocess
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

# Create Buck2 MCP server
mcp = FastMCP("Buck2")


def run_buck2_command(args: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
    """Run a buck2 command and return the result"""
    try:
        cmd = ["buck2"] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd(),
            check=False
        )
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "command": " ".join(cmd)
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "buck2 command not found. Please ensure Buck2 is installed and in PATH.",
            "returncode": 127,
            "command": " ".join(["buck2"] + args)
        }


@mcp.tool()
def buck2_build(targets: str) -> Dict[str, Any]:
    """Build Buck2 targets
    
    Args:
        targets: Target patterns to build (e.g., "//...", "//path/to:target")
    """
    args = ["build", targets]
    return run_buck2_command(args)


@mcp.tool()
def buck2_test(targets: str) -> Dict[str, Any]:
    """Run Buck2 tests
    
    Args:
        targets: Test target patterns (e.g., "//...", "//path/to:test")
    """
    args = ["test", targets]
    return run_buck2_command(args)


@mcp.tool()
def buck2_query(query: str, output_format: str = "json") -> Dict[str, Any]:
    """Query Buck2 build graph
    
    Args:
        query: Buck2 query expression (e.g., "deps(//...)", "kind(rust_binary, //...)")
        output_format: Output format (json, dot, thrift_binary)
    """
    args = ["cquery", query, "--output-format", output_format]
    result = run_buck2_command(args)
    
    # Try to parse JSON output if format is json
    if output_format == "json" and result["success"]:
        try:
            result["parsed_output"] = json.loads(result["stdout"])
        except json.JSONDecodeError:
            pass
    
    return result


@mcp.tool()
def buck2_targets(pattern: str = "//...") -> Dict[str, Any]:
    """List Buck2 targets matching pattern
    
    Args:
        pattern: Target pattern to list (default: "//...")
    """
    args = ["targets", pattern]
    return run_buck2_command(args)


@mcp.resource("buck2-config://")
def get_buck2_config() -> str:
    """Get Buck2 configuration from .buckconfig files"""
    config_files = [".buckconfig", ".buckconfig.local"]
    config_content = {}
    
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config_content[config_file] = f.read()
            except Exception as e:
                config_content[config_file] = f"Error reading {config_file}: {str(e)}"
        else:
            config_content[config_file] = "File not found"
    
    return json.dumps(config_content, indent=2)


@mcp.resource("buck2-root://")
def get_buck2_root() -> str:
    """Get Buck2 project root information"""
    try:
        result = run_buck2_command(["root", "--kind=project"])
        if result["success"]:
            root_path = result["stdout"].strip()
            return json.dumps({
                "project_root": root_path,
                "buck_files": list(Path(root_path).glob("**/BUCK")) if os.path.exists(root_path) else []
            }, indent=2, default=str)
        else:
            return json.dumps({"error": result["stderr"]}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')