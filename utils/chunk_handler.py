import logging
import re

import tiktoken

def content_split(content: str) -> dict:
    """Split content into chunks, separated by two newlines."""
    # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    encoding = tiktoken.get_encoding("cl100k_base")
    try:
        chunks = content.split('\n\n')
        tokens = []
        characters = []
        for chunk in chunks:
            tokens.append(len(encoding.encode(chunk)))
            characters.append(len(chunk))
    except Exception as e:
        logging.error(f'content_split: {str(e)}')
        chunks = [content]
        tokens = [len(encoding.encode(content))]
        characters = [len(content)]
    return {'chunks': chunks, 'tokens': tokens, 'characters': characters}

def group_chunks(split_chunks: dict, min_size: int, max_size: int,
                 group_by: str) -> list:  # group_by: 'tokens' or 'characters'
    """Group very short chunks, to form approximately page long chunks."""
    chunks = split_chunks['chunks']
    values = split_chunks[group_by]
    grouped_chunks = []
    current_chunk = ''
    current_value = 0
    try:
        for chunk, value in zip(chunks, values):
            if value > max_size:
                # Use regex to split the chunk at symbol boundaries
                split_points = re.finditer(r'[\s.,;!?]+', chunk)
                last_split_end = 0
                for match in split_points:
                    if match.start() - last_split_end >= max_size:
                        grouped_chunks.append(chunk[last_split_end:match.start()] + '\n')
                        last_split_end = match.start()
                # Append the remaining part of the chunk
                if last_split_end < len(chunk):
                    grouped_chunks.append(chunk[last_split_end:] + '\n')
            else:
                grouped_chunks.append(current_chunk)
                current_chunk = chunk
                current_value = value

        if current_chunk:
            grouped_chunks.append(current_chunk)
    except Exception as e:
        logging.error(f'group_chunks: {str(e)}')
        grouped_chunks = chunks

    return grouped_chunks
