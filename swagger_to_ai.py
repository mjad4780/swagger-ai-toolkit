#!/usr/bin/env python3
"""
swagger_to_ai.py - Convert OpenAPI/Swagger JSON to AI-friendly Markdown
نسخة متطورة للتعامل مع المراجع الدائرية المعقدة
"""

import json
import sys
import os
from typing import Dict, Any, List, Optional, Set, Tuple
import argparse
import re


class SwaggerToAI:
    def __init__(self, swagger_data: Dict[str, Any]):
        self.data = swagger_data
        self.components = swagger_data.get('components', {})
        self.schemas = self.components.get('schemas', {})
        self.paths = swagger_data.get('paths', {})
        self.output_lines = []
        self.visited_refs: Set[str] = set()
        self.max_depth = 10  # الحد الأقصى للعمق
        self.ref_counter = 0  # عداد للمراجع الفريدة

    def resolve_ref(self, ref: str, depth: int = 0) -> Any:
        """Resolve $ref مع التحكم في العمق"""
        if depth > self.max_depth:
            return {"type": "object", "description": f"⚠️ Max depth reached for: {ref}"}
        
        if not ref.startswith('#/'):
            return ref
        
        # إنشاء مفتاح فريد لكل مرجع + عمق
        ref_key = f"{ref}_{depth}"
        if ref_key in self.visited_refs:
            return {"type": "object", "description": f"⚠️ Circular reference detected: {ref} (depth {depth})"}
        
        self.visited_refs.add(ref_key)
        
        path = ref[2:].split('/')
        current = self.data
        for part in path:
            if part in current:
                current = current[part]
            else:
                self.visited_refs.remove(ref_key)
                return {'error': f'Cannot resolve reference: {ref}'}
        
        # إذا كان المرجع يحتوي على مرجع آخر
        if isinstance(current, dict) and '$ref' in current:
            result = self.resolve_ref(current['$ref'], depth + 1)
            self.visited_refs.remove(ref_key)
            return result
        
        self.visited_refs.remove(ref_key)
        return current

    def simplify_schema(self, schema: Any, depth: int = 0) -> Any:
        """تبسيط الـ schema ومنع التكرار"""
        if schema is None:
            return {"type": "null"}
        
        if isinstance(schema, str):
            if schema.startswith('#/'):
                return self.resolve_ref(schema, depth)
            return schema

        if not isinstance(schema, dict):
            return schema

        # إذا كان مجرد مرجع
        if '$ref' in schema:
            resolved = self.resolve_ref(schema['$ref'], depth)
            if isinstance(resolved, dict):
                return self.simplify_schema(resolved, depth + 1)
            return resolved

        result = schema.copy()
        
        # معالجة allOf, anyOf, oneOf
        for combine_type in ['allOf', 'anyOf', 'oneOf']:
            if combine_type in result:
                combined = []
                for item in result[combine_type]:
                    simplified = self.simplify_schema(item, depth + 1)
                    if isinstance(simplified, dict):
                        combined.append(simplified)
                if combined:
                    # دمج المخططات
                    merged = self.merge_schemas(combined)
                    # إزالة key الجمع ونضع خصائص المدمج
                    if 'properties' in merged:
                        result['properties'] = merged.get('properties', {})
                    if 'required' in merged:
                        result['required'] = merged.get('required', [])
                del result[combine_type]

        # معالجة الـ array
        if result.get('type') == 'array' and 'items' in result:
            result['items'] = self.simplify_schema(result['items'], depth + 1)
            if isinstance(result['items'], dict) and result['items'].get('type') == 'object':
                pass  # نتركها كما هي

        # معالجة الـ object properties
        if 'properties' in result:
            for prop_name, prop_schema in result['properties'].items():
                result['properties'][prop_name] = self.simplify_schema(prop_schema, depth + 1)

        return result

    def merge_schemas(self, schemas: List[Dict]) -> Dict:
        """دمج عدة schemas في واحد"""
        merged = {}
        for schema in schemas:
            if not isinstance(schema, dict):
                continue
            
            # دمج properties
            if 'properties' in schema:
                if 'properties' not in merged:
                    merged['properties'] = {}
                merged['properties'].update(schema['properties'])
            
            # دمج required
            if 'required' in schema:
                if 'required' not in merged:
                    merged['required'] = []
                merged['required'].extend(schema['required'])
        
        return merged

    def parse_schema(self, schema: Any, depth: int = 0) -> str:
        """تحويل schema إلى نص مع منع التكرار"""
        if depth > self.max_depth:
            return "⚠️ Max depth exceeded"
        
        if schema is None:
            return "null"
        
        # تبسيط الـ schema أولاً
        simplified = self.simplify_schema(schema, depth)
        
        if not isinstance(simplified, dict):
            return str(simplified)

        result = []
        indent = "  " * depth

        # Handle type
        schema_type = simplified.get('type', 'object')
        
        # Handle enum
        if 'enum' in simplified:
            enum_values = [str(v) for v in simplified['enum']]
            return f"enum: {', '.join(enum_values)}"

        # Handle array
        if schema_type == 'array':
            items = simplified.get('items', {})
            if isinstance(items, dict):
                item_desc = self.parse_schema(items, depth + 1)
                return f"Array of:\n{item_desc}"
            else:
                return f"Array of: {items}"

        # Handle object
        if schema_type == 'object' or 'properties' in simplified:
            properties = simplified.get('properties', {})
            required = simplified.get('required', [])
            
            if not properties:
                return "object (no properties defined)"
            
            for prop_name, prop_schema in properties.items():
                is_required = "required" if prop_name in required else "optional"
                # معالجة خاصة للـ refs
                if isinstance(prop_schema, dict) and 'description' in prop_schema and 'Recursive reference' in prop_schema['description']:
                    result.append(f"{indent}- {prop_name} ({is_required}): {prop_schema['description']}")
                else:
                    prop_desc = self.parse_schema(prop_schema, depth + 1)
                    result.append(f"{indent}- {prop_name} ({is_required}): {prop_desc}")
            
            return '\n'.join(result)

        # Handle primitive types
        if schema_type in ['string', 'number', 'integer', 'boolean']:
            desc = schema_type
            if 'format' in simplified:
                desc += f" ({simplified['format']})"
            if 'description' in simplified:
                desc += f" - {simplified['description']}"
            return desc

        # Handle any other type
        if 'description' in simplified:
            return simplified['description']
        
        return str(simplified) if simplified else "object"

    def parse_parameters(self, params: List[Dict]) -> str:
        """Parse parameters with better error handling"""
        if not params:
            return "None"
        
        result = []
        for param in params:
            try:
                name = param.get('name', '')
                location = param.get('in', '')
                required = 'required' if param.get('required', False) else 'optional'
                schema = param.get('schema', {})
                
                self.visited_refs.clear()
                # تبسيط الـ schema أولاً
                simplified_schema = self.simplify_schema(schema, 0)
                schema_desc = self.parse_schema(simplified_schema, 1)
                result.append(f"- {name} ({location}, {required}): {schema_desc}")
            except Exception as e:
                result.append(f"- {param.get('name', 'unknown')}: Error parsing - {str(e)}")
        
        return '\n'.join(result)

    def parse_request_body(self, request_body: Dict) -> str:
        """Parse request body with better error handling"""
        if not request_body:
            return "None"
        
        try:
            if '$ref' in request_body:
                request_body = self.resolve_ref(request_body['$ref'], 0)
            
            content = request_body.get('content', {})
            if not content:
                return "No content defined"
            
            content_type = next(iter(content.keys())) if content else 'application/json'
            schema = content.get(content_type, {}).get('schema', {})
            
            self.visited_refs.clear()
            simplified_schema = self.simplify_schema(schema, 0)
            return self.parse_schema(simplified_schema, 1)
        except Exception as e:
            return f"Error parsing request body: {str(e)}"

    def parse_response(self, response: Dict) -> str:
        """Parse response with better error handling"""
        if not response:
            return "No response defined"
        
        try:
            if '$ref' in response:
                response = self.resolve_ref(response['$ref'], 0)
            
            content = response.get('content', {})
            if not content:
                description = response.get('description', 'No description')
                return f"Description: {description}"
            
            content_type = next(iter(content.keys())) if content else 'application/json'
            schema = content.get(content_type, {}).get('schema', {})
            
            self.visited_refs.clear()
            simplified_schema = self.simplify_schema(schema, 0)
            return self.parse_schema(simplified_schema, 1)
        except Exception as e:
            return f"Error parsing response: {str(e)}"

    def process_endpoint(self, path: str, methods: Dict[str, Any]):
        """Process a single endpoint with better error handling"""
        for method, details in methods.items():
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                continue
            
            try:
                tags = details.get('tags', ['Untagged'])
                summary = details.get('summary', '')
                description = details.get('description', '')
                parameters = details.get('parameters', [])
                request_body = details.get('requestBody', {})
                responses = details.get('responses', {})
                
                self.output_lines.append(f"## {tags[0] if tags else 'Untagged'}\n")
                self.output_lines.append(f"### {method.upper()} {path}\n")
                
                if summary:
                    self.output_lines.append(f"**Summary:** {summary}\n")
                if description:
                    self.output_lines.append(f"**Description:** {description}\n")
                
                # Headers
                headers = [p for p in parameters if p.get('in') == 'header']
                if headers:
                    self.output_lines.append("**Headers:**\n")
                    self.output_lines.append(self.parse_parameters(headers) + "\n")
                
                # Request Body
                if request_body:
                    self.output_lines.append("**Request Body:**\n")
                    self.output_lines.append(self.parse_request_body(request_body) + "\n")
                
                # Success Response (2xx)
                success_responses = {code: resp for code, resp in responses.items() 
                                   if code.startswith('2')}
                if success_responses:
                    self.output_lines.append("**Success Response:**\n")
                    for code, response in success_responses.items():
                        self.output_lines.append(f"Status {code}:\n")
                        self.output_lines.append(self.parse_response(response) + "\n")
                
                # Error Responses (4xx, 5xx)
                error_responses = {code: resp for code, resp in responses.items() 
                                 if code.startswith('4') or code.startswith('5')}
                if error_responses:
                    self.output_lines.append("**Error Responses:**\n")
                    codes = sorted(error_responses.keys())
                    self.output_lines.append(f"Status Codes: {', '.join(codes)}\n")
                
                self.output_lines.append("---\n")
                
            except Exception as e:
                self.output_lines.append(f"## Error processing {method.upper()} {path}: {str(e)}\n")
                self.output_lines.append("---\n")

    def generate(self) -> str:
        """Generate the complete Markdown output"""
        self.output_lines = ["# API Documentation for AI\n\n"]
        
        # Process all endpoints with error handling
        for path, methods in self.paths.items():
            self.process_endpoint(path, methods)
        
        return '\n'.join(self.output_lines)


def main():
    parser = argparse.ArgumentParser(
        description='Convert OpenAPI/Swagger JSON to AI-friendly Markdown'
    )
    parser.add_argument(
        'input_file',
        help='Path to OpenAPI/Swagger JSON file'
    )
    parser.add_argument(
        '-o', '--output',
        default='api_for_ai.md',
        help='Output Markdown file (default: api_for_ai.md)'
    )
    
    args = parser.parse_args()
    
    try:
        # قراءة الملف مع معالجة الأخطاء
        with open(args.input_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # محاولة تنظيف الملف من أي مشاكل
            swagger_data = json.loads(content)
        
        # توليد الماركداون
        converter = SwaggerToAI(swagger_data)
        markdown = converter.generate()
        
        # كتابة الملف
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"✅ Successfully generated {args.output}")
        print(f"💡 Note: Some complex circular references may have been simplified.")
        
    except FileNotFoundError:
        print(f"❌ Error: File '{args.input_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON format - {e}")
        print("💡 Try checking if the file is a valid OpenAPI/Swagger JSON file.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()