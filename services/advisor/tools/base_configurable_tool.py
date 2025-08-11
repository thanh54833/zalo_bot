import logging
from typing import Dict, Any, Type, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, create_model, Field

logger = logging.getLogger(__name__)


class BaseConfigurableTool(BaseTool):
    """
    Base class cho tất cả tools phải lấy config từ app_config.json
    NGHIÊM CẤM hard-code bất kỳ thông tin gì!
    """
    
    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        """
        Khởi tạo tool với config từ file
        
        Args:
            tool_config: Config dictionary từ app_config.json
            **kwargs: Additional arguments cho BaseTool
        """
        # ✅ LƯU CONFIG VÀO LOCAL
        self._tool_config = tool_config
        self._tool_name = tool_config.get("name", "unknown_tool")
        
        # ✅ TỰ ĐỘNG TẠO TẤT CẢ PROPERTIES
        self._auto_generate_all_properties()
        
        # ✅ GỌI CONSTRUCTOR CHA VỚI PROPERTIES ĐÃ TẠO
        super().__init__(
            name=self._generate_tool_name(),
            description=self._generate_tool_description(),
            args_schema=self._generate_input_schema(),
            **kwargs
        )
        
        logger.info(f"🚀 Configurable tool '{self.name}' initialized from config!")
    
    def _auto_generate_all_properties(self):
        """TỰ ĐỘNG TẠO tất cả tool properties từ config"""
        try:
            # ✅ LẤY TỪ CONFIG - KHÔNG HARD-CODE!
            self._input_config = self._tool_config.get("input", {})
            self._param_config = self._input_config.get("param", {})
            self._body_config = self._input_config.get("body", {})
            self._output_config = self._tool_config.get("output", {})
            self._dependencies = self._tool_config.get("dependencies", [])
            self._category = self._tool_config.get("category", "unknown")
            
            logger.debug(f"✅ Properties generated for {self._tool_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate properties: {e}")
            # Set defaults nếu có lỗi
            self._input_config = {}
            self._param_config = {}
            self._body_config = {}
            self._output_config = {}
            self._dependencies = []
            self._category = "unknown"
    
    def _generate_tool_name(self) -> str:
        """Tự động tạo tên tool từ config"""
        return self._tool_name
    
    def _generate_tool_description(self) -> str:
        """Tự động tạo mô tả từ config"""
        return self._tool_config.get("description", "No description available")
    
    def _generate_input_schema(self) -> Type[BaseModel]:
        """Tự động tạo Pydantic input schema từ config"""
        fields = {}
        
        # ✅ TỰ ĐỘNG TẠO query parameter fields
        if self._param_config:
            for param_name, param_def in self._param_config.items():
                field_type = self._auto_map_type(param_def.get("type", "string"))
                field_description = param_def.get("description", f"Parameter: {param_name}")
                field_default = param_def.get("default")
                field_required = param_def.get("required", False)
                
                if field_default is not None:
                    fields[param_name] = (
                        field_type,
                        Field(
                            default=field_default,
                            description=field_description
                        )
                    )
                else:
                    fields[param_name] = (
                        field_type,
                        Field(
                            description=field_description
                        )
                    )
        
        # ✅ TỰ ĐỘNG TẠO body fields
        if self._body_config:
            for body_name, body_def in self._body_config.items():
                field_type = self._auto_map_type(body_def.get("type", "string"))
                field_description = body_def.get("description", f"Body field: {body_name}")
                field_required = body_def.get("required", False)
                
                if field_required:
                    fields[body_name] = (
                        field_type,
                        Field(
                            description=field_description
                        )
                    )
                else:
                    fields[body_name] = (
                        field_type,
                        Field(
                            default=None,
                            description=field_description
                        )
                    )
        
        # Tự động tạo model class
        model_name = f"{self._tool_name.capitalize()}Input"
        return create_model(model_name, **fields)
    
    def _auto_map_type(self, config_type: str) -> Type:
        """Tự động map config types sang Pydantic types"""
        type_mapping = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        return type_mapping.get(config_type, str)
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get thông tin config của tool"""
        return {
            "name": self._tool_name,
            "type": self._tool_config.get("type"),
            "category": self._category,
            "dependencies": self._dependencies,
            "input_params": list(self._param_config.keys()) if self._param_config else [],
            "body_fields": list(self._body_config.keys()) if self._body_config else []
        } 