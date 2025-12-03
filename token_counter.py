import sys
import ast
import tokenize
from io import BytesIO

class CodeCleaner(ast.NodeTransformer):
    """
    Removes specific nodes from the AST to exclude them from the count.
    """
    def visit_Assert(self, node):
        return None  # Remove assert statements

    def visit_Import(self, node):
        return None  # Remove 'import x'

    def visit_ImportFrom(self, node):
        return None  # Remove 'from x import y'

def count_tokens_in_file(file_path: str) -> int:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return 0

    # 1. AST CLEANING
    # Parse code, remove imports/asserts, and regenerate the string.
    try:
        tree = ast.parse(source_code)
        cleaner = CodeCleaner()
        tree = cleaner.visit(tree)
        ast.fix_missing_locations(tree)
        cleaned_code = ast.unparse(tree)
    except SyntaxError as e:
        print(f"Syntax Error in source file: {e}")
        return 0

    # 2. TOKEN COUNTING
    # Tokenize the cleaned code and count relevant tokens.
    tokens = tokenize.tokenize(BytesIO(cleaned_code.encode('utf-8')).readline)
    
    count = 0
    # Tokens to ignore (structure and comments)
    ignored_tokens = {
        tokenize.COMMENT,
        tokenize.NL,        # Non-terminating newline
        tokenize.NEWLINE,   # Terminating newline
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENCODING,
        tokenize.ENDMARKER
    }

    for token in tokens:
        if token.type not in ignored_tokens:
            count += 1

    return count

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python token_counter.py <path_to_file.py>")
        sys.exit(1)

    target_file = sys.argv[1]
    total_tokens = count_tokens_in_file(target_file)
    
    print(f"File: {target_file}")
    print(f"Functional Tokens: {total_tokens}")