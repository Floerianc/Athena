from typing import (
    Optional,
    TYPE_CHECKING
)

from chromadb.api.types import (
    Document,
    Documents
)

from Athena.common.logger import log_event
from Athena.common.utils import chars_to_tokens
from Athena.config import Config

if TYPE_CHECKING:
    from cli.progress import ProgressBar


class DocumentNormalizer:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.chunk_size = chars_to_tokens(self.config.parse_chunk_size)

    def _lengthen_doc(
        self,
        length: int,
        chunk_size: int,
        content: Documents,
        index: int,
        sep: str = " "
    ) -> Document:
        """_lengthen_doc Fallback function

        This is a fallback function for files that
        enforce being parsed by chunks.

        This is quite complex and seriously ugly, but essentially
        it takes the content of a line and looks for the max chunk size
        to save the excess in the same line, essentially lengthening each line
        to amount of `chunk_size`.

        For example:\n
        'Hello how are you'\n
        'doing my friend'\n
        gets turned into\n

        'Hello how are you doing my' <-- reached max chunk size\n
        'friend' <-- anything outside of chunk size remains untouched

        Args:
            length (int): Length of line
            chunk_size (int): Max chunk size
            content (Documents): Every line from the file
            index (int): Current index of the line in `content`
            sep (str, optional): Seperator between lines. Defaults to " ".

        Returns:
            Document: Lengthened line
        """
        start = index
        end = index + 1
        total_length = length
        last_index = len(content) - 1

        while True:
            is_last = end > last_index
            new_doc: Document = content[end] if not is_last else ""

            total_length += len(new_doc)
            if total_length >= chunk_size:
                excess = total_length - chunk_size
                lengthened_doc = sep.join(content[start:end+1])       # start until end string

                if excess > 0:
                    cutoff = lengthened_doc[:chunk_size]    # everything up until chunk size
                    overflow = lengthened_doc[chunk_size:]          # overflow
                    content[end] = overflow
                    lengthened_doc = cutoff

                del content[start:end-1]
                break
            elif is_last:
                lengthened_doc = sep.join(content[start:end])
                del content[start:end-1]
                break
            else:
                end += 1
        return lengthened_doc

    def _shorten_doc(
        self, 
        chunk_size: int, 
        index: int, 
        current_item: Document, 
        content: Documents
    ) -> Document:
        """_shorten_doc Fallback function

        This is the opposite of _lengthen_doc() as this
        shortens a line from the File and inserts the excess
        into the next line.

        Args:
            chunk_size (int): Max chunk size
            index (int): Current index in the list
            current_item (Document): Current line string
            content (Documents): Full list of every string

        Returns:
            Document: Shortened string
        """
        chunk = current_item[0:chunk_size]
        content.insert(index+1, current_item[chunk_size:])
        return chunk
    
    @log_event("Chunking text file documents...")
    def normalize_document_lengths(
        self, 
        content: Documents,
        progress_bar: Optional['ProgressBar'] = None,
    ) -> Documents:
        """normalize_document_lengths I hate this

        This is the primary fallback function for files that enforce the
        normalizing of document lengths. This is to save tokens for each
        database input while remaining consistent with every input length.
        
        This took way too long to code and is ridiculously ugly, but it works
        as a fallback.

        Args:
            progress_bar (ProgressBar): Progress bar
            content (Documents): List of every line in the file

        Returns:
            Documents: List of every normalized line
        """
        # I spent like 1.5 hours on trying to make this work 
        # just to realise that I am already chunking data
        # with another function so this is quite useless but
        # idgaf this is now just a smart utility tool :)
        chunk_size = self.chunk_size
        
        for index, doc in enumerate(content):
            if progress_bar:
                progress_bar.steps = len(content)
                progress_bar.advance_step()

            length = len(doc)
            
            if length < chunk_size:
                content[index] = self._lengthen_doc(
                    length=length,
                    chunk_size=chunk_size,
                    content=content,
                    index=index
                )
            elif length > chunk_size:
                content[index] = self._shorten_doc(
                    chunk_size=chunk_size,
                    index=index,
                    current_item=content[index],
                    content=content
                )
        return content