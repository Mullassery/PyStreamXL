"""MCP Connector for PyStreamXL - Excel & Spreadsheet Processing"""

import json
import logging
import subprocess
import tempfile
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from statguardian._mcp_connector import BaseMCPConnector
except ImportError:
    class BaseMCPConnector(ABC):
        def __init__(self, project_name: str, port: int = 8765):
            self.project_name = project_name
            self.port = port
            self.dab_process: Optional[subprocess.Popen] = None
            self._ready = False

        @abstractmethod
        def get_mcp_tools(self) -> Dict[str, Any]:
            pass

        @abstractmethod
        def get_tool_handlers(self) -> Any:
            pass

        def start_mcp_connector(self) -> str:
            logger.info(f"Starting {self.project_name} MCP...")
            try:
                tools = self.get_mcp_tools()
                self.handler = self.get_tool_handlers()
                config = self._generate_dab_config(tools)
                config_path = self._write_temp_config(config)
                self._start_dab_subprocess(config_path)
                self._ready = True
                return f"http://localhost:{self.port}/mcp"
            except Exception as e:
                logger.error(f"Failed: {e}")
                raise

        def stop_mcp_connector(self):
            if self.dab_process:
                try:
                    self.dab_process.terminate()
                    self.dab_process.wait(timeout=5)
                except (subprocess.TimeoutExpired, OSError):
                    pass
                self._ready = False

        def _generate_dab_config(self, tools: Dict[str, Any]) -> Dict:
            return {
                "runtime": {"host": "0.0.0.0", "port": self.port, "cors": {"origins": ["*"]}},
                "entities": {k: {"source": k, "permissions": [{"actions": ["*"], "roles": ["*"]}]} for k in tools.keys()},
                "rest": {"enabled": True, "path": "/api"},
                "graphql": {"enabled": True, "path": "/graphql"},
                "mcp": {"enabled": True, "path": "/mcp"},
            }

        def _write_temp_config(self, config: Dict) -> str:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(config, f)
                return f.name

        def _start_dab_subprocess(self, config_path: str):
            self.dab_process = subprocess.Popen(
                ["dab", "start", "--config", config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        def is_ready(self) -> bool:
            return self._ready


class SpreadsheetProcessor:
    """Excel and spreadsheet processing"""

    def __init__(self):
        self.mcp_connector: Optional[Any] = None

    def start_mcp_connector(self, port: int = 8781) -> str:
        from pystreaxl._mcp_tools import PyStreamXLMCPHandler, PyStreamXLMCPTools
        self.mcp_connector = _MCPXLConnector(excel=self, port=port)
        return self.mcp_connector.start_mcp_connector()

    def stop_mcp_connector(self):
        if self.mcp_connector:
            self.mcp_connector.stop_mcp_connector()


class _MCPXLConnector(BaseMCPConnector):
    def __init__(self, excel: SpreadsheetProcessor, port: int = 8781):
        super().__init__("PyStreamXL", port=port)
        self.excel = excel

    def get_mcp_tools(self) -> Dict[str, Any]:
        from pystreaxl._mcp_tools import PyStreamXLMCPTools
        return PyStreamXLMCPTools.get_tools()

    def get_tool_handlers(self) -> Any:
        from pystreaxl._mcp_tools import PyStreamXLMCPHandler
        return PyStreamXLMCPHandler(self.excel)
