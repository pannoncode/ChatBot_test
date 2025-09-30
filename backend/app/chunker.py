from unstructured.chunking.basic import chunk_elements

import uuid


def chunk_basic(elements, max_characters: int = 500, new_after_n_chars: int = 400, overlap: int = 100):
    return chunk_elements(
        elements=elements,
        max_characters=max_characters,
        new_after_n_chars=new_after_n_chars,
        overlap=overlap)


def created_doc_chunks(elements, file_name: str):
    chunks_result = chunk_basic(elements)

    documents_chunk = []

    for i, chunk in enumerate(chunks_result):
        text = (getattr(chunk, "text", "") or "").strip()
        pid = str(uuid.uuid5(uuid.NAMESPACE_URL,
                             f"{file_name}|basic|{i}|{text[:64]}"))

        documents_chunk.append(
            {
                "id": pid,
                "filename": file_name,
                "strategy": "basic",
                "category": chunk.category if hasattr(chunk, 'category') else "Document",
                "metadata": chunk.metadata if hasattr(chunk, 'metadata') else {},
                "text": chunk.text,
            }
        )

    return documents_chunk


def file_type_separator_chunk_gen(file_ext: str, file_path: str, file_name: str):
    if file_ext == "pdf":
        from unstructured.partition.pdf import partition_pdf
        elements = partition_pdf(file_path)
    elif file_ext == "txt":
        from unstructured.partition.text import partition_text
        elements = partition_text(file_path)
    elif file_ext == "docx":
        from unstructured.partition.docx import partition_docx
        elements = partition_docx(file_path)
    elif file_ext == "md":
        from unstructured.partition.md import partition_md
        elements = partition_md(file_path)
    else:
        raise ValueError(f"Unsupported file extension: {file_ext}")

    return created_doc_chunks(elements=elements, file_name=file_name)
