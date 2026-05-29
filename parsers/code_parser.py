"""Code file parsing for C, Java, and Scala."""
import re
import logging
from typing import List, Dict
from pathlib import Path

import tiktoken

from parsers.pdf_parser import ParsedChunkData

logger = logging.getLogger(__name__)


class CodeParser:
    """Parse code files into semantic chunks."""

    def __init__(self):
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        try:
            return len(self.tokenizer.encode(text))
        except:
            return len(text) // 4

    def parse_code_file(self, file_path: str, file_type: str) -> List[ParsedChunkData]:
        """
        Parse code file and extract semantic chunks.

        Args:
            file_path: Path to code file
            file_type: File type (c, java, scala)

        Returns:
            List of ParsedChunkData objects
        """
        logger.info(f"Parsing code file: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if not content.strip():
                logger.warning(f"Empty file: {file_path}")
                return []

            # Parse based on file type
            if file_type == 'c':
                chunks = self._parse_c_file(content, file_path)
            elif file_type == 'java':
                chunks = self._parse_java_file(content, file_path)
            elif file_type == 'scala':
                chunks = self._parse_scala_file(content, file_path)
            else:
                # Fallback: treat as plain text
                chunks = self._parse_generic(content, file_path, file_type)

            logger.info(f"Extracted {len(chunks)} chunks from: {file_path}")
            return chunks

        except Exception as e:
            logger.error(f"Error parsing code file {file_path}: {e}")
            raise

    def _parse_c_file(self, content: str, file_path: str) -> List[ParsedChunkData]:
        """Parse C file."""
        chunks = []
        chunk_index = 0

        # Extract functions using regex
        # Pattern: return_type function_name(params) { ... }
        function_pattern = re.compile(
            r'((?:static|extern|inline)?\s*\w+\s+\*?\s*(\w+)\s*\([^)]*\)\s*\{)',
            re.MULTILINE
        )

        # Also extract struct definitions
        struct_pattern = re.compile(
            r'(struct\s+(\w+)\s*\{[^}]+\};?)',
            re.MULTILINE | re.DOTALL
        )

        # Find all structs
        for match in struct_pattern.finditer(content):
            struct_text = match.group(0)
            struct_name = match.group(2)
            line_start = content[:match.start()].count('\n') + 1

            chunks.append(ParsedChunkData(
                chunk_index=chunk_index,
                chunk_type='code',
                content=struct_text,
                metadata={
                    'language': 'c',
                    'file_path': file_path,
                    'element_type': 'struct',
                    'element_name': struct_name,
                    'line_start': line_start
                },
                token_count=self.count_tokens(struct_text)
            ))
            chunk_index += 1

        # Find all functions
        lines = content.split('\n')
        for match in function_pattern.finditer(content):
            func_start = match.start()
            func_name = match.group(2)
            line_start = content[:func_start].count('\n') + 1

            # Find matching closing brace
            func_body = self._extract_braced_block(content, func_start)

            if func_body:
                # Include preceding comment if present
                preceding_comment = self._extract_preceding_comment(lines, line_start - 1)
                if preceding_comment:
                    func_body = preceding_comment + '\n' + func_body

                chunks.append(ParsedChunkData(
                    chunk_index=chunk_index,
                    chunk_type='code',
                    content=func_body,
                    metadata={
                        'language': 'c',
                        'file_path': file_path,
                        'element_type': 'function',
                        'element_name': func_name,
                        'line_start': line_start
                    },
                    token_count=self.count_tokens(func_body)
                ))
                chunk_index += 1

        # If no functions found, create one chunk for entire file
        if not chunks:
            chunks.append(ParsedChunkData(
                chunk_index=0,
                chunk_type='code',
                content=content,
                metadata={
                    'language': 'c',
                    'file_path': file_path,
                    'element_type': 'file',
                    'element_name': Path(file_path).name
                },
                token_count=self.count_tokens(content)
            ))

        return chunks

    def _parse_java_file(self, content: str, file_path: str) -> List[ParsedChunkData]:
        """Parse Java file."""
        chunks = []
        chunk_index = 0

        # Extract package and imports (keep with first class)
        package_imports = self._extract_package_imports(content)

        # Extract classes
        class_pattern = re.compile(
            r'((?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*class\s+(\w+))',
            re.MULTILINE
        )

        lines = content.split('\n')

        for match in class_pattern.finditer(content):
            class_start = match.start()
            class_name = match.group(2)
            line_start = content[:class_start].count('\n') + 1

            # Extract class body
            class_body = self._extract_braced_block(content, class_start)

            if class_body:
                # Add package/imports to first class
                if chunk_index == 0 and package_imports:
                    class_body = package_imports + '\n\n' + class_body

                # Check if class is small enough for one chunk
                class_tokens = self.count_tokens(class_body)

                if class_tokens <= 1000:
                    # Small class: one chunk
                    chunks.append(ParsedChunkData(
                        chunk_index=chunk_index,
                        chunk_type='code',
                        content=class_body,
                        metadata={
                            'language': 'java',
                            'file_path': file_path,
                            'element_type': 'class',
                            'element_name': class_name,
                            'line_start': line_start
                        },
                        token_count=class_tokens
                    ))
                    chunk_index += 1
                else:
                    # Large class: split into methods
                    method_chunks = self._extract_java_methods(class_body, class_name, file_path)
                    for method_chunk in method_chunks:
                        chunks.append(ParsedChunkData(
                            chunk_index=chunk_index,
                            chunk_type='code',
                            content=method_chunk['content'],
                            metadata={
                                'language': 'java',
                                'file_path': file_path,
                                'element_type': 'method',
                                'element_name': method_chunk['name'],
                                'class_name': class_name,
                                'line_start': line_start
                            },
                            token_count=self.count_tokens(method_chunk['content'])
                        ))
                        chunk_index += 1

        # Fallback: entire file as one chunk
        if not chunks:
            chunks.append(ParsedChunkData(
                chunk_index=0,
                chunk_type='code',
                content=content,
                metadata={
                    'language': 'java',
                    'file_path': file_path,
                    'element_type': 'file',
                    'element_name': Path(file_path).name
                },
                token_count=self.count_tokens(content)
            ))

        return chunks

    def _parse_scala_file(self, content: str, file_path: str) -> List[ParsedChunkData]:
        """Parse Scala file."""
        # Scala is similar to Java for our purposes
        chunks = []
        chunk_index = 0

        # Extract package and imports
        package_imports = self._extract_package_imports(content)

        # Extract objects and classes
        class_pattern = re.compile(
            r'((?:case\s+)?(?:class|object|trait)\s+(\w+))',
            re.MULTILINE
        )

        for match in class_pattern.finditer(content):
            class_start = match.start()
            class_name = match.group(2)
            line_start = content[:class_start].count('\n') + 1

            # Extract class/object body
            class_body = self._extract_braced_block(content, class_start)

            if class_body:
                if chunk_index == 0 and package_imports:
                    class_body = package_imports + '\n\n' + class_body

                chunks.append(ParsedChunkData(
                    chunk_index=chunk_index,
                    chunk_type='code',
                    content=class_body,
                    metadata={
                        'language': 'scala',
                        'file_path': file_path,
                        'element_type': 'class',
                        'element_name': class_name,
                        'line_start': line_start
                    },
                    token_count=self.count_tokens(class_body)
                ))
                chunk_index += 1

        # Fallback
        if not chunks:
            chunks.append(ParsedChunkData(
                chunk_index=0,
                chunk_type='code',
                content=content,
                metadata={
                    'language': 'scala',
                    'file_path': file_path,
                    'element_type': 'file',
                    'element_name': Path(file_path).name
                },
                token_count=self.count_tokens(content)
            ))

        return chunks

    def _parse_generic(self, content: str, file_path: str, file_type: str) -> List[ParsedChunkData]:
        """Generic parsing for unknown file types."""
        return [ParsedChunkData(
            chunk_index=0,
            chunk_type='code',
            content=content,
            metadata={
                'language': file_type,
                'file_path': file_path,
                'element_type': 'file',
                'element_name': Path(file_path).name
            },
            token_count=self.count_tokens(content)
        )]

    def _extract_braced_block(self, content: str, start_pos: int) -> str:
        """Extract content from start_pos to matching closing brace."""
        # Find first opening brace
        brace_start = content.find('{', start_pos)
        if brace_start == -1:
            return None

        # Find matching closing brace
        brace_count = 0
        for i in range(brace_start, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return content[start_pos:i + 1]

        return None

    def _extract_preceding_comment(self, lines: List[str], line_idx: int) -> str:
        """Extract comment block immediately preceding a line."""
        comment_lines = []

        # Go backwards from line_idx
        for i in range(line_idx - 1, max(0, line_idx - 20), -1):
            line = lines[i].strip()

            if line.startswith('//') or line.startswith('/*') or line.startswith('*'):
                comment_lines.insert(0, lines[i])
            elif line:
                break

        return '\n'.join(comment_lines) if comment_lines else None

    def _extract_package_imports(self, content: str) -> str:
        """Extract package and import statements."""
        lines = content.split('\n')
        package_imports = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('package ') or stripped.startswith('import '):
                package_imports.append(line)
            elif stripped and not stripped.startswith('//'):
                # Stop at first non-import statement
                break

        return '\n'.join(package_imports) if package_imports else None

    def _extract_java_methods(self, class_body: str, class_name: str, file_path: str) -> List[Dict]:
        """Extract methods from Java class body."""
        methods = []

        # Method pattern: access_modifier return_type method_name(params) { ... }
        method_pattern = re.compile(
            r'((?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*\{)',
            re.MULTILINE
        )

        for match in method_pattern.finditer(class_body):
            method_name = match.group(2)
            method_start = match.start()

            method_body = self._extract_braced_block(class_body, method_start)
            if method_body:
                methods.append({
                    'name': method_name,
                    'content': method_body
                })

        return methods


if __name__ == "__main__":
    # Test code parser
    parser = CodeParser()

    # Find a code file to test
    import glob
    code_files = glob.glob("/home/cedrik/AI-Tutor/modules/**/src/**/*.java", recursive=True)

    if code_files:
        test_file = code_files[0]
        print(f"\nTesting code parser with: {test_file}")

        chunks = parser.parse_code_file(test_file, 'java')
        print(f"\nExtracted {len(chunks)} chunks")

        if chunks:
            print(f"\nFirst chunk:")
            print(f"  Type: {chunks[0].chunk_type}")
            print(f"  Metadata: {chunks[0].metadata}")
            print(f"  Tokens: {chunks[0].token_count}")
            print(f"  Content preview: {chunks[0].content[:200]}...")
    else:
        print("No code files found to test")
