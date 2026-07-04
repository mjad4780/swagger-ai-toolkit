#!/usr/bin/env python3
"""
swagger_to_ai.py - Convert OpenAPI/Swagger JSON to AI-Ready Markdown
Generates separate Markdown files per tag (category) by default.
Supports OpenAPI 2.0 and 3.0 with full $ref resolution.
"""

import json
import sys
import os
import argparse
import logging
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SwaggerToAI:
    def __init__(self, swagger_data: Dict[str, Any]):
        self.data = swagger_data
        self.components = swagger_data.get('components', {})
        self.schemas = self.components.get('schemas', {})
        self.paths = swagger_data.get('paths', {})
        self.visited_refs: Set[str] = set()
        self.max_depth = 10
        self.output_lines = []  # Used when generating a single file

    def resolve_ref(self, ref: str, depth: int = 0) -> Any:
        """Resolve $ref with depth limit and circular detection"""
        if depth > self.max_depth:
            return {"type": "object", "description": f"⚠️ Max depth reached for: {ref}"}
        if not ref.startswith('#/'):
            return ref
        ref_key = f"{ref}_{depth}"
        if ref_key in self.visited_refs:
            return {"type": "object", "description": f"⚠️ Circular reference detected: {ref}"}
        self.visited_refs.add(ref_key)
        path = ref[2:].split('/')
        current = self.data
        for part in path:
            if part in current:
                current = current[part]
            else:
                self.visited_refs.remove(ref_key)
                return {'error': f'Cannot resolve reference: {ref}'}
        if isinstance(current, dict) and '$ref' in current:
            result = self.resolve_ref(current['$ref'], depth + 1)
            self.visited_refs.remove(ref_key)
            return result
        self.visited_refs.remove(ref_key)
        return current

    def simplify_schema(self, schema: Any, depth: int = 0) -> Any:
        """Simplify schema and resolve references"""
        if schema is None:
            return {"type": "null"}
        if isinstance(schema, str):
            if schema.startswith('#/'):
                return self.resolve_ref(schema, depth)
            return schema
        if not isinstance(schema, dict):
            return schema
        if '$ref' in schema:
            resolved = self.resolve_ref(schema['$ref'], depth)
            if isinstance(resolved, dict):
                return self.simplify_schema(resolved, depth + 1)
            return resolved
        result = schema.copy()
        for combine_type in ['allOf', 'anyOf', 'oneOf']:
            if combine_type in result:
                combined = []
                for item in result[combine_type]:
                    simplified = self.simplify_schema(item, depth + 1)
                    if isinstance(simplified, dict):
                        combined.append(simplified)
                if combined:
                    merged = self.merge_schemas(combined)
                    if 'properties' in merged:
                        result['properties'] = merged.get('properties', {})
                    if 'required' in merged:
                        result['required'] = merged.get('required', [])
                del result[combine_type]
        if result.get('type') == 'array' and 'items' in result:
            result['items'] = self.simplify_schema(result['items'], depth + 1)
        if 'properties' in result:
            for prop_name, prop_schema in result['properties'].items():
                result['properties'][prop_name] = self.simplify_schema(prop_schema, depth + 1)
        return result

    def merge_schemas(self, schemas: List[Dict]) -> Dict:
        merged = {}
        for schema in schemas:
            if not isinstance(schema, dict):
                continue
            if 'properties' in schema:
                if 'properties' not in merged:
                    merged['properties'] = {}
                merged['properties'].update(schema['properties'])
            if 'required' in schema:
                if 'required' not in merged:
                    merged['required'] = []
                merged['required'].extend(schema['required'])
        return merged

    def parse_schema(self, schema: Any, depth: int = 0) -> str:
        """Convert schema to readable string"""
        if depth > self.max_depth:
            return "⚠️ Max depth exceeded"
        if schema is None:
            return "null"
        simplified = self.simplify_schema(schema, depth)
        if not isinstance(simplified, dict):
            return str(simplified)
        result = []
        indent = "  " * depth
        schema_type = simplified.get('type', 'object')
        if 'enum' in simplified:
            enum_values = [str(v) for v in simplified['enum']]
            return f"enum: {', '.join(enum_values)}"
        if schema_type == 'array':
            items = simplified.get('items', {})
            if isinstance(items, dict):
                item_desc = self.parse_schema(items, depth + 1)
                return f"Array of:\n{item_desc}"
            else:
                return f"Array of: {items}"
        if schema_type == 'object' or 'properties' in simplified:
            properties = simplified.get('properties', {})
            required = simplified.get('required', [])
            if not properties:
                return "object (no properties defined)"
            for prop_name, prop_schema in properties.items():
                is_required = "required" if prop_name in required else "optional"
                if isinstance(prop_schema, dict) and 'description' in prop_schema and 'Recursive reference' in prop_schema['description']:
                    result.append(f"{indent}- {prop_name} ({is_required}): {prop_schema['description']}")
                else:
                    prop_desc = self.parse_schema(prop_schema, depth + 1)
                    result.append(f"{indent}- {prop_name} ({is_required}): {prop_desc}")
            return '\n'.join(result)
        if schema_type in ['string', 'number', 'integer', 'boolean']:
            desc = schema_type
            if 'format' in simplified:
                desc += f" ({simplified['format']})"
            if 'description' in simplified:
                desc += f" - {simplified['description']}"
            return desc
        if 'description' in simplified:
            return simplified['description']
        return str(simplified) if simplified else "object"

    def parse_parameters(self, params: List[Dict]) -> str:
        if not params:
            return "None"
        result = []
        for param in params:
            name = param.get('name', '')
            location = param.get('in', '')
            required = 'required' if param.get('required', False) else 'optional'
            schema = param.get('schema', {})
            simplified_schema = self.simplify_schema(schema, 0)
            schema_desc = self.parse_schema(simplified_schema, 1)
            result.append(f"- {name} ({location}, {required}): {schema_desc}")
        return '\n'.join(result)

    def parse_request_body(self, request_body: Dict) -> str:
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
            simplified_schema = self.simplify_schema(schema, 0)
            return self.parse_schema(simplified_schema, 1)
        except Exception as e:
            return f"Error parsing request body: {str(e)}"

    def parse_response(self, response: Dict) -> str:
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
            simplified_schema = self.simplify_schema(schema, 0)
            return self.parse_schema(simplified_schema, 1)
        except Exception as e:
            return f"Error parsing response: {str(e)}"

    def process_endpoint(self, path: str, method: str, details: Dict) -> List[str]:
        """Process a single endpoint and return a list of markdown lines"""
        lines = []
        tags = details.get('tags', ['Untagged'])
        summary = details.get('summary', '')
        description = details.get('description', '')
        parameters = details.get('parameters', [])
        request_body = details.get('requestBody', {})
        responses = details.get('responses', {})

        lines.append(f"### {method.upper()} {path}\n")
        if summary:
            lines.append(f"**Summary:** {summary}\n")
        if description:
            lines.append(f"**Description:** {description}\n")

        headers = [p for p in parameters if p.get('in') == 'header']
        if headers:
            lines.append("**Headers:**\n")
            lines.append(self.parse_parameters(headers) + "\n")

        if request_body:
            lines.append("**Request Body:**\n")
            lines.append(self.parse_request_body(request_body) + "\n")

        success_responses = {code: resp for code, resp in responses.items() if code.startswith('2')}
        if success_responses:
            lines.append("**Success Response:**\n")
            for code, response in success_responses.items():
                lines.append(f"Status {code}:\n")
                lines.append(self.parse_response(response) + "\n")

        error_responses = {code: resp for code, resp in responses.items() if code.startswith('4') or code.startswith('5')}
        if error_responses:
            lines.append("**Error Responses:**\n")
            codes = sorted(error_responses.keys())
            lines.append(f"Status Codes: {', '.join(codes)}\n")

        lines.append("---\n")
        return lines, tags

    def generate_single(self) -> str:
        """Generate a single Markdown file (legacy mode)"""
        self.output_lines = ["# API Documentation for AI\n\n"]
        for path, methods in self.paths.items():
            for method, details in methods.items():
                if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                    continue
                lines, _ = self.process_endpoint(path, method, details)
                self.output_lines.extend(lines)
        return '\n'.join(self.output_lines)

    def generate_split(self, output_dir: str) -> Dict[str, str]:
        """
        Generate separate Markdown files per tag.
        Returns a dict mapping tag name to its markdown content.
        """
        # Group endpoints by tag
        tag_groups = defaultdict(list)
        for path, methods in self.paths.items():
            for method, details in methods.items():
                if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                    continue
                lines, tags = self.process_endpoint(path, method, details)
                # If multiple tags, add the endpoint to each tag group
                for tag in tags:
                    tag_groups[tag].extend(lines)

        # Build content per tag
        result = {}
        for tag, lines in tag_groups.items():
            # Clean tag name for filename
            safe_tag = tag.lower().replace(' ', '_').replace('/', '_')
            header = f"# {tag} API Endpoints\n\n"
            content = header + ''.join(lines)
            result[tag] = content

        # Also create an index file listing all tags
        index_lines = ["# API Tags Index\n\n"]
        for tag in sorted(result.keys()):
            index_lines.append(f"- [{tag}]({tag.lower().replace(' ', '_').replace('/', '_')}.md)\n")
        result['_index'] = ''.join(index_lines)

        # Write files to disk
        os.makedirs(output_dir, exist_ok=True)
        for tag, content in result.items():
            if tag == '_index':
                filename = os.path.join(output_dir, 'README.md')
            else:
                safe_tag = tag.lower().replace(' ', '_').replace('/', '_')
                filename = os.path.join(output_dir, f"{safe_tag}.md")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"✅ Written: {filename}")

        return result


def main():
    parser = argparse.ArgumentParser(
        description='Convert OpenAPI/Swagger JSON to AI-Ready Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate separate files per tag (default)
  python swagger_to_ai.py swagger.json

  # Generate a single file instead
  python swagger_to_ai.py swagger.json --single -o api.md

  # Specify output directory for split files
  python swagger_to_ai.py swagger.json --output-dir my_docs
        """
    )
    parser.add_argument('input', help='Path to OpenAPI/Swagger JSON file')
    parser.add_argument('-o', '--output', help='Output file name (for single file mode)')
    parser.add_argument('--output-dir', default='api_docs', help='Output directory for split files (default: api_docs)')
    parser.add_argument('--single', action='store_true', help='Generate a single Markdown file instead of splitting by tag')
    parser.add_argument('--verbose', action='store_true', help='Show detailed logs')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"File '{args.input}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        sys.exit(1)

    converter = SwaggerToAI(data)

    if args.single:
        # Single file mode
        output_file = args.output or 'api_for_ai.md'
        content = converter.generate_single()
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"✅ Single file generated: {output_file}")
    else:
        # Split mode (default)
        converter.generate_split(args.output_dir)
        logger.info(f"✅ All files generated in directory: {args.output_dir}/")
        print(f"\n📁 Check the '{args.output_dir}/' folder for tag-based Markdown files.")
        print(f"   The index file is '{args.output_dir}/README.md'.")


if __name__ == "__main__":
    main()