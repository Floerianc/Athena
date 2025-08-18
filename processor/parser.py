from PyPDF2 import PdfReader
from typing import List
from Athena.core.config import Config
from chromadb import Documents
from Athena.processor.normalizer import DocumentNormalizer
from Athena.common.types import (
    TextParsings,
    MDChapter,
    MDChapters
)
from Athena.common.utils import chars_to_tokens
from Athena.common.logger import log_event

class DocumentParser:
    def __init__(self, config: Config, file_path: str) -> None:
        self.config = config
        self.filename = file_path
        self.normalizer = DocumentNormalizer(self.config)
        self.chunk_size = chars_to_tokens(self.config.parse_chunk_size)
    
    def _contains_blank_lines(
        self, 
        text: str
    ) -> bool:
        """_contains_blank_lines If content contains blank lines

        This checks every line in content string for a blank line.

        Args:
            text (str): Any string

        Returns:
            bool: True if there are blank lines
        """
        return any(not line.strip() for line in text.splitlines())
    
    def _contains_large_lines(
        self, 
        text: str
    ) -> bool:
        """_contains_large_lines If content has large lines

        Returns a boolean to tell if any string contains very long
        lines.
        
        This is partially to determine the parsing technique for
        plain-text inputs.
        
        It uses the parse_chunk_size config value as a reference
        to check if a line is extraordinary long.

        Args:
            text (str): Any string lol

        Returns:
            bool: True if contains very long lines.
        """
        return any(len(line) >= self.chunk_size * 2 for line in text.splitlines())
    
    @log_event("Parsing text by blank lines...")
    def parse_by_blank(
        self, 
        text: str
    ) -> List[str]:
        """parse_by_blank Parses plain text

        Parses plain text content by blank lines

        Args:
            text (str): Any string

        Returns:
            List[str]: List of strings
        """
        return [line for line in text.splitlines() if line.strip()]
    
    @log_event("Parsing text by newlines...")
    def parse_by_newline(self, text: str) -> List[str]:
        """parse_by_newline Parses plain text

        Parses plain text content by newlines.

        Args:
            text (str): Any string :)

        Returns:
            List[str]: List of strings
        """
        return text.split("\n")
    
    @log_event("Parsing text by chunks...")
    def parse_by_chunk(
        self, 
        text: str
    ) -> List[str]:
        """parse_by_chunk Parses plain text

        If the file is for example just one very large line
        it doesn't make sense to parse by newlines or anything
        so this instead stores it as a list of chunks.
        
        The chunk size can be modified in the configuration file.

        Args:
            text (str): Any string

        Returns:
            List[str]: List of string chunks.
        """
        output_lines = []
        length = len(text)
        chunk_size = self.chunk_size
        i0 = 0
        i1 = lambda: i0 + chunk_size
        
        while True:
            i = i1() if i1() <= length else length
            chunk = text[i0:i]
            output_lines.append(chunk)
            i0 = i
            if i >= length:
                break
        return output_lines
    
    @log_event("Turning text file into documents...")
    def txt_to_documents(
        self, 
        filter_method: TextParsings, 
        text: str
    ) -> Documents:
        """txt_to_documents Converts text to Documents

        This method converts a plain text file into
        ChromaDB database ready Documents.

        Raises:
            ValueError: If the parsing method can't be found

        Returns:
            Documents: List of Strings for the database
        """
        # holy shit this is ugly
        match filter_method:
            case TextParsings.AUTO:
                if self._contains_blank_lines(text):
                    return self.parse_by_blank(text)
                else:
                    if self._contains_large_lines(text):
                        return self.parse_by_chunk(text)
                    else:
                        return self.parse_by_newline(text)
            case TextParsings.BY_BLANK:
                return self.parse_by_blank(text)
            case TextParsings.BY_NEWLINE:
                return self.parse_by_newline(text)
            case TextParsings.BY_CHUNK:
                return self.parse_by_chunk(text)
            case _:
                raise ValueError(f"Unknown text parsing method: {filter_method}")
    
    def pdf_to_documents(self) -> Documents:
        reader = PdfReader(self.filename)
        docs = [page.extract_text() for page in reader.pages]
        
        parsing_type = self.config.txt_parsing
        docs = "\n".join(docs)
        return self.txt_to_documents(
            filter_method=parsing_type,
            text=docs
        )
    
    def _get_md_level(self, line: str) -> int:
        return len(line) - len(line.lstrip("#"))
    
    def _get_next_chapter_index(
        self, 
        lines: List[str], 
        cur_chapter: int
    ) -> int:
        for index, line in enumerate(lines[cur_chapter+1:], start=cur_chapter+1):
            if line.startswith("#"):
                return index
        return len(lines) - 1
    
    def _get_chapter_content(
        self,
        all_lines: list[str],
        chapter_index: int
    ) -> str:
        start = chapter_index
        stop = self._get_next_chapter_index(lines=all_lines, cur_chapter=chapter_index)
        return r"\n".join(all_lines[start:stop])
    
    def _get_chapters(
        self, 
        md_content: str
    ) -> MDChapters:
        lines = md_content.splitlines()
        chapters = []
        
        for index, line in enumerate(lines):
            if line.startswith("#"):
                level = self._get_md_level(line)
                chapters_content = self._get_chapter_content(lines, index)
                chapters.append(MDChapter(level=level, index=index, content=chapters_content))
        return chapters
    
    def _has_subchapter(
        self, 
        chapters: MDChapters, 
        cur_chapter: MDChapter
    ) -> bool:
        index = chapters.index(cur_chapter)
        if chapters[index+1].get("level") > cur_chapter.get("level"):
            return True
        else:
            return False
    
    def _chapters_to_documents(
        self,
        chapters: MDChapters,
        docs: Documents,
        level: int = 2
    ) -> None:
        # TODO: Idea: Have following flow:
        # For each chapter:
        #       1. Check token length for chapter + all subchapters
        #       2. If len(chapter + all subchapters) > token count
        #           3.1 Go down one sub chapter
        #           3.2 Go back to 2
        #       2.1 else if len(chapters + all subchapters) > token count and no unvisited subchapters
        #           3.3 Fallback to parsing by chunk size
        #       2.2 else
        #           3.4 append to documents
        #       4. After every chapter return documents

        i = 1
        while i < len(chapters):
            current = chapters[i]
            children = []
            i += 1
            while i < len(chapters) and chapters[i]["level"] > current["level"]:
                children.append(chapters[i])
                i += 1

            token_count = chars_to_tokens(len(current["content"]))
            if token_count <= self.chunk_size:
                docs.append(current["content"])
            elif children:
                self._chapters_to_documents(children, docs, level=level+1)
            else:
                # Fallback - chunking
                chunks = self.parse_by_chunk(current["content"])
                docs.extend(chunks)
    
    def md_to_documents(
        self,
        text: str
    ) -> Documents:
        chapters = self._get_chapters(text)
        docs = []
        self._chapters_to_documents(chapters, docs)

        if self.config.enforce_uniform_chunks:
            docs = self.normalizer.normalize_document_lengths(docs)
        return docs


if __name__ == "__main__":
    pass