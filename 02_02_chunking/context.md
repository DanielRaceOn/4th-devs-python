
Proces wyszukiwania jest fundamentalnym elementem koncepcji łączenia modelu językowego z zewnętrznymi źródłami wiedzy. Obecnie za wyszukiwanie niemal zawsze odpowiadają agenci (Agentic RAG), posługując się narzędziami wyszukiwawczymi lub nawet pełnoprawnymi silnikami wyszukiwania, na przykład [Algolia](https://algolia.com/) lub [Qdrant](https://qdrant.tech/). 

Powiedzieliśmy już, że indeksowanie polega na podziale treści na mniejsze fragmenty (chunki/dokumenty), składające się z głównej **zawartości** oraz **metadanych** opisujących dany dokument. Długość pojedynczego dokumentu rzadko przekracza 200–500 słów lub 500-1500 tokenów. Dzięki temu podczas procesu wyszukiwania **zapytanie** użytkownika może zostać precyzyjnie **dopasowane** do ich treści albo na podstawie zapisu (full-text lub fuzzy-search) albo poprzez dopasowanie **znaczeniowe** (tzw. semantic search). 

Tutaj pojawia się pytanie z nieoczywistą odpowiedzią, czyli: **"w jaki sposób tworzyć dokumenty?"**, które koniecznie musi uwzględniać także: **"w jaki sposób agent będzie do nich docierał?"**. Pod uwagę możemy wziąć rzeczy takie jak:

1. **Znaki:** to podział według liczby znaków, przydatny przy nieustrukturyzowanej treści
2. **Separatory:** to podział według separatorów (np. nagłówków), zwykle wykonywany rekurencyjnie (nagłówki -> akapity -> zdania -> znaki) w celu osiągnięcia podobnej długości dokumentów. 
3. **Kontekst:** uwzględnia wzbogacanie fragmentów z pomocą LLM, poprzez generowanie dla nich kontekstu na podstawie otaczających fragmentów, bądź nawet treści całego dokumentu. Technika została przedstawiona przez [Anthropic](https://www.anthropic.com/engineering/contextual-retrieval). 
4. **Tematyka:** uwzględnia pełne wykorzystanie modelu (bądź nawet agentów) do generowania fragmentów od podstaw na podstawie treści dokumentu. 


##############


‎04-03-2025 10:05 AM
Over the years, I have collaborated closely with ML engineering leaders across various industries, guiding them on how to make the right chunking strategy decisions for their Retrieval-Augmented Generation (RAG) use cases. One of the biggest challenges I’ve observed is the lack of clear, practical guidance on how to effectively structure and segment source documents to maximize retrieval quality and LLM performance.

To bridge this gap, I embarked on a journey to document the best practices and implementation strategies for optimal chunking in RAG workflows — specifically on Databricks. This guide is the culmination of that effort, providing a comprehensive breakdown of leading chunking techniques, practical code examples, and industry-proven methodologies to help you build high-performance RAG systems in 2025 and beyond.

If you’re looking to refine your RAG pipeline, ensure efficient retrieval, and avoid common pitfalls in chunking, this guide has everything you need.


Why Chunking Matters in RAG
Chunking is simply the act of splitting larger documents into smaller units (“chunks”). Each chunk can be individually indexed, embedded, and retrieved. Because RAG pipelines often rely on retrieval from vector databases and large language models (LLMs) with limited context windows, smart chunking can make all the difference in delivering relevant, context-rich answers.

According to an article by UnDatas, “The main goal of chunking is to segment complex data into more digestible pieces. This improves retrieval accuracy and reduces computational overhead.”

Key reasons to invest in a strong chunking strategy include:

Context Window Constraints: Both embedding models and LLMs have strict context size limits. Well-sized chunks ensure no chunk exceeds these boundaries.
Improved Retrieval Efficiency: Precise and smaller chunks often mean faster lookups and better recall.
Computational Optimization: Appropriate chunk sizes can reduce unnecessary processing.
Enhanced Relevance: Maintaining semantic integrity ensures more accurate matches and ultimately better answers.
Where Chunking Fits in the RAG Pipeline
A typical RAG system consists of:

Indexing — Convert documents into vector embeddings and store them in a vector database.
Retrieval — Query the database for the most relevant chunks.
Augmentation — Inject retrieved chunks into the LLM prompt.
Generation — Prompt the LLM to produce a final, context-informed response.
Chunking happens in the preprocessing stage (part of the indexing workflow). Its quality directly affects the retrieval phase, shaping how relevant or comprehensive the context is for downstream generation.

Overview of Chunking Strategies
1. Fixed-Size Chunking
Concept
This is the simplest approach, segmenting text into equally sized pieces (using character, token, or word counts). Often, an overlap is introduced to maintain continuity of ideas.

Example with LangChain (Character-based):

from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document

def perform_fixed_size_chunking(document, chunk_size=1000, chunk_overlap=200😞
    """
    Performs fixed-size chunking on a document with specified overlap.
    
    Args:
        document (str): The text document to process
        chunk_size (int): The target size of each chunk in characters
        chunk_overlap (int): The number of characters of overlap between chunks
        
    Returns:
        list: The chunked documents with metadata
    """
    # Create the text splitter with optimal parameters
    text_splitter = CharacterTextSplitter(
        separator="\n\n",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    
    # Split the text into chunks
    chunks = text_splitter.split_text(document)
    print(f"Document split into {len(chunks)} chunks")
    
    # Convert to Document objects with metadata
    documents = []
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk,
            metadata={
                "chunk_id": i,
                "total_chunks": len(chunks),
                "chunk_size": len(chunk),
                "chunk_type": "fixed-size"
            }
        )
        documents.append(doc)
    
    return documents

# Example usage
if __name__ == "__main__":
    
    # Create the dummy document
    document = create_dummy_document()
    
    # Process with fixed-size chunking
    chunked_docs = perform_fixed_size_chunking(
        document,
        chunk_size=1000,
        chunk_overlap=200
    )
    
    # Display results
    print("\n----- CHUNKING RESULTS -----")
    print(f"Total chunks: {len(chunked_docs)}")
    
    # Print an example chunk
    print("\n----- EXAMPLE CHUNK -----")
    middle_chunk_idx = len(chunked_docs) // 2
    example_chunk = chunked_docs[middle_chunk_idx]
    print(f"Chunk {middle_chunk_idx} content ({len(example_chunk.page_content)} characters):")
    print("-" * 40)
    print(example_chunk.page_content)
    print("-" * 40)
    print(f"Metadata: {example_chunk.metadata}")
    
    # For integration with Databricks Vector Search
    print("\nThese documents are ready for embedding and storage in Databricks Vector Search")
    print("Example next steps:")
    print("1. Create embeddings using the Databricks embedding endpoint")
    print("2. Store documents and embeddings in Delta table")
    print("3. Create Vector Search index for retrieval")
Advantages

Straightforward and easy to implement.
Uniform chunk size simplifies batch operations.
Works decently for content that doesn’t heavily rely on semantic context.
Drawbacks

May cut off sentences or paragraphs abruptly.
Ignores natural semantic breaks.
Relevant information can end up scattered across chunks.
Best Fit: Relatively uniform documents with consistent formatting, such as simple logs or straightforward text.

2. Semantic Chunking
Concept
Instead of arbitrarily slicing text by length, semantic chunking splits documents at logical boundaries (e.g., sentences, paragraphs, or sections). Often, consecutive segments that are highly similar may be merged, providing coherent text blocks.

Example with LangChain (Recursive approach):

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import re

def perform_semantic_chunking(document, chunk_size=500, chunk_overlap=100😞
    """
    Performs semantic chunking on a document using recursive character splitting 
    at logical text boundaries.
    
    Args:
        document (str): The text document to process
        chunk_size (int): The target size of each chunk in characters
        chunk_overlap (int): The number of characters of overlap between chunks
        
    Returns:
        list: The semantically chunked documents with metadata
    """
    # Create the text splitter with semantic separators
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", " ", ""],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    
    # Split the text into semantic chunks
    semantic_chunks = text_splitter.split_text(document)
    print(f"Document split into {len(semantic_chunks)} semantic chunks")
    
    # Determine section titles for enhanced metadata
    section_patterns = [
        r'^#+\s+(.+)$',      # Markdown headers
        r'^.+\n[=\-]{2,}$',  # Underlined headers
        r'^[A-Z\s]+:$'       # ALL CAPS section titles
    ]
    
    # Convert to Document objects with enhanced metadata
    documents = []
    current_section = "Introduction"
    
    for i, chunk in enumerate(semantic_chunks):
        # Try to identify section title from chunk
        chunk_lines = chunk.split('\n')
        for line in chunk_lines:
            for pattern in section_patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    current_section = match.group(0)
                    break
        
        # Calculate semantic density (ratio of non-stopwords to total words)
        words = re.findall(r'\b\w+\b', chunk.lower())
        stopwords = ['the', 'and', 'is', 'of', 'to', 'a', 'in', 'that', 'it', 'with', 'as', 'for']
        content_words = [w for w in words if w not in stopwords]
        semantic_density = len(content_words) / max(1, len(words))
        
        doc = Document(
            page_content=chunk,
            metadata={
                "chunk_id": i,
                "total_chunks": len(semantic_chunks),
                "chunk_size": len(chunk),
                "chunk_type": "semantic",
                "section": current_section,
                "semantic_density": round(semantic_density, 2)
            }
        )
        documents.append(doc)
    
    return documents

# Example usage with Databricks integration
if __name__ == "__main__":

    # Create the dummy document
    document = create_dummy_document()
    
    # Process with semantic chunking
    chunked_docs = perform_semantic_chunking(
        document,
        chunk_size=500,
        chunk_overlap=100
    )
    
    # Display results
    print("\n----- CHUNKING RESULTS -----")
    print(f"Total semantic chunks: {len(chunked_docs)}")
    
    # Print an example chunk
    print("\n----- EXAMPLE SEMANTIC CHUNK -----")
    middle_chunk_idx = len(chunked_docs) // 2
    example_chunk = chunked_docs[middle_chunk_idx]
    print(f"Chunk {middle_chunk_idx} content ({len(example_chunk.page_content)} characters):")
    print("-" * 40)
    print(example_chunk.page_content)
    print("-" * 40)
    print(f"Metadata: {example_chunk.metadata}")
    
    # Optional: Calculate section distribution for analysis
    section_counts = {}
    for doc in chunked_docs:
        section = doc.metadata["section"]
        section_counts[section] = section_counts.get(section, 0) + 1
    
    print("\n----- SECTION DISTRIBUTION -----")
    for section, count in section_counts.items():
        print(f"{section}: {count} chunks")
    
    # For integration with Databricks embeddings
    print("\nTo integrate with Databricks:")
    print("1. Create embeddings using the Databricks embedding API:")
    print("   from langchain_community.embeddings import DatabricksEmbeddings")
    print("   embeddings = DatabricksEmbeddings(endpoint='databricks-bge-large-en')")
    print("2. Store documents and embeddings in Delta table")
    print("3. Create Vector Search index using the semantic metadata for filtering")
Advantages

Preserves the flow of ideas.
Keeps related concepts together, boosting retrieval accuracy.
Helpful for documents like articles or academic papers that have clear sections.
Drawbacks

More complex to implement.
Yields variable chunk sizes.
Slightly higher computational requirements.
Best Fit: Well-structured, narrative, or academic documents where continuity is crucial.

3. Recursive Chunking
Concept
Recursive chunking relies on a hierarchy of separators. The algorithm attempts to split on high-level separators first, then moves to increasingly finer separators if chunks remain too large.

Example for Python code:

from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_core.documents import Document
import re

def perform_code_chunking(code_document, language="python", chunk_size=100, chunk_overlap=15😞
    """
    Performs recursive chunking on code documents using language-aware splitting.
    
    Args:
        code_document (str): The code document to process
        language (str): Programming language of the code
        chunk_size (int): The target size of each chunk in characters
        chunk_overlap (int): The number of characters of overlap between chunks
        
    Returns:
        list: The chunked code as Document objects with metadata
    """
    # Create language-specific splitter using the updated API
    if language.lower() == "python":
        code_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    elif language.lower() == "javascript":
        code_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.JS,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    elif language.lower() == "java":
        code_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.JAVA,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    elif language.lower() == "go":
        code_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.GO,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    elif language.lower() == "rust":
        code_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.RUST,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    else:
        # Fallback to generic code splitting
        code_splitter = RecursiveCharacterTextSplitter(
            separators=["\nclass ", "\ndef ", "\n\n", "\n", " ", ""],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        
    # Split the code into chunks
    code_chunks = code_splitter.split_text(code_document)
    print(f"Code document split into {len(code_chunks)} chunks")
    
    # Extract functions and classes for better metadata
    documents = []
    for i, chunk in enumerate(code_chunks):
        # Try to identify code structure
        function_match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', chunk)
        class_match = re.search(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', chunk)
        import_match = re.search(r'import\s+([a-zA-Z_][a-zA-Z0-9_\.]*)', chunk)
        
        # Determine chunk type
        chunk_type = "code_segment"
        if function_match:
            chunk_type = "function"
            structure_name = function_match.group(1)
        elif class_match:
            chunk_type = "class"
            structure_name = class_match.group(1)
        elif import_match:
            chunk_type = "import"
            structure_name = import_match.group(1)
        else:
            structure_name = f"segment_{i}"
        
        # Create document with enhanced metadata
        doc = Document(
            page_content=chunk,
            metadata={
                "chunk_id": i,
                "total_chunks": len(code_chunks),
                "language": language,
                "chunk_type": chunk_type,
                "structure_name": structure_name,
                "lines": chunk.count('\n') + 1
            }
        )
        documents.append(doc)
    
    return documents

# Create an example Python document for testing
def create_python_document():
    """
    Creates a sample Python document for testing code chunking.
    """
    python_code = """
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# Load and prepare data
def load_data(filepath):
    \"\"\"
    Load data from CSV file
    
    Args:
        filepath: Path to the CSV file
        
    Returns:
        Pandas DataFrame containing the data
    \"\"\"
    df = pd.read_csv(filepath)
    print(f"Loaded data with {df.shape[0]} rows and {df.shape[1]} columns")
    return df

def preprocess_data(df, target_column):
    \"\"\"
    Preprocess the data for training
    
    Args:
        df: Input DataFrame
        target_column: Name of the target column
        
    Returns:
        X, y for model training
    \"\"\"
    # Handle missing values
    df = df.fillna(df.mean())
    
    # Split features and target
    X = df.drop(target_column, axis=1)
    y = df[target_column]
    
    return X, y

class ModelTrainer:
    \"\"\"
    Class to handle model training and evaluation
    \"\"\"
    def __init__(self, model_type='rf', random_state=42):
        \"\"\"Initialize the trainer\"\"\"
        self.random_state = random_state
        if model_type == 'rf':
            self.model = RandomForestClassifier(random_state=random_state)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    def train(self, X, y, test_size=0.2):
        \"\"\"Train the model with train-test split\"\"\"
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.random_state
        )
        
        # Train the model
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_preds = self.model.predict(X_train)
        test_preds = self.model.predict(X_test)
        
        train_acc = accuracy_score(y_train, train_preds)
        test_acc = accuracy_score(y_test, test_preds)
        
        print(f"Training accuracy: {train_acc:.4f}")
        print(f"Testing accuracy: {test_acc:.4f}")
        
        return {
            'model': self.model,
            'X_test': X_test,
            'y_test': y_test,
            'test_acc': test_acc
        }
    
    def get_feature_importance(self, feature_names):
        \"\"\"Get feature importance from the model\"\"\"
        if not hasattr(self.model, 'feature_importances_'):
            raise ValueError("Model doesn't have feature importances")
        
        importances = self.model.feature_importances_
        indices = np.argsort(importances)[::-1]
        
        result = []
        for i in indices:
            result.append({
                'feature': feature_names[i],
                'importance': importances[i]
            })
        
        return result

# Main execution
if __name__ == "__main__":
    # Example usage
    filepath = "data/dataset.csv"
    df = load_data(filepath)
    
    X, y = preprocess_data(df, target_column="target")
    
    trainer = ModelTrainer(model_type='rf')
    results = trainer.train(X, y, test_size=0.25)
    
    # Print feature importance
    importances = trainer.get_feature_importance(X.columns)
    print("\\nFeature Importance:")
    for item in importances[:5]:
        print(f"- {item['feature']}: {item['importance']:.4f}")
"""
    return python_code

# Example usage with Databricks integration
if __name__ == "__main__":
    # Create Python code document
    python_document = create_python_document()
    
    # Process with code chunking
    chunked_docs = perform_code_chunking(
        python_document,
        language="python",
        chunk_size=100,
        chunk_overlap=15
    )
    
    # Display results
    print("\n----- CHUNKING RESULTS -----")
    print(f"Total code chunks: {len(chunked_docs)}")
    
    # Print chunk types distribution
    chunk_types = {}
    for doc in chunked_docs:
        chunk_type = doc.metadata["chunk_type"]
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
    
    print("\n----- CODE STRUCTURE BREAKDOWN -----")
    for chunk_type, count in chunk_types.items():
        print(f"{chunk_type}: {count} chunks")
    
    # Print an example function chunk
    print("\n----- EXAMPLE FUNCTION CHUNK -----")
    function_chunks = [doc for doc in chunked_docs if doc.metadata["chunk_type"] == "function"]
    if function_chunks:
        example_chunk = function_chunks[0]
        print(f"Function: {example_chunk.metadata['structure_name']}")
        print("-" * 40)
        print(example_chunk.page_content)
        print("-" * 40)
    
    # For integration with Databricks
    print("\nTo use with Databricks:")
    print("1. Store code chunks in Delta table with metadata")
    print("2. Create embeddings using:")
    print("   from langchain_community.embeddings import DatabricksEmbeddings")
    print("   embeddings = DatabricksEmbeddings(endpoint='databricks-bge-large-en')")
    print("3. Create Vector Search index for code retrieval")
    print("4. Use function/class metadata for filtering during retrieval")
Advantages

Creates more context-aware splits than simple fixed-size approaches.
Especially powerful for structured text or code, where block-based splitting is crucial.
Drawbacks

More complicated to configure.
Requires domain-specific separators for best results (like “def” or “class” in Python).
Best Fit: Technical documents with a clear structure, especially code repositories or structured reports.

4. Adaptive Chunking
Concept
Adaptive chunking changes chunk sizes based on text complexity. Simpler sections become larger chunks, denser or more intricate sections become smaller chunks.

Example (pseudo-code style):

import re
import nltk
from nltk.tokenize import sent_tokenize
from langchain_core.documents import Document
from langchain_text_splitters import TextSplitter
import numpy as np

# You might need to download NLTK resources in Databricks
# This can be run once at the start of your notebook
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class AdaptiveTextSplitter(TextSplitter😞
    """
    Custom text splitter that adapts chunk sizes based on text complexity.
    """
    
    def __init__(
        self,
        min_chunk_size: int = 300,
        max_chunk_size: int = 1000,
        min_chunk_overlap: int = 30,
        max_chunk_overlap: int = 150,
        complexity_measure: str = "lexical_density",
        length_function=len,
        **kwargs
    😞
        """Initialize with parameters for adaptive chunking.
        
        Args:
            min_chunk_size: Minimum size for chunks with highest complexity
            max_chunk_size: Maximum size for chunks with lowest complexity
            min_chunk_overlap: Minimum overlap between chunks
            max_chunk_overlap: Maximum overlap for complex chunks
            complexity_measure: Method to measure text complexity 
                                (options: "lexical_density", "sentence_length", "combined")
            length_function: Function to measure text length
        """
        super().__init__(**kwargs)
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.min_chunk_overlap = min_chunk_overlap
        self.max_chunk_overlap = max_chunk_overlap
        self.complexity_measure = complexity_measure
        self.length_function = length_function
    
    def analyze_complexity(self, text: str) -> float:
        """
        Analyze the complexity of text and return a score between 0 and 1.
        Higher score means more complex text.
        """
        if not text.strip():
            return 0.0
        
        # Lexical density: ratio of unique words to total words
        if self.complexity_measure == "lexical_density" or self.complexity_measure == "combined":
            words = re.findall(r'\b\w+\b', text.lower())
            if not words:
                lex_density = 0
            else:
                unique_words = set(words)
                lex_density = len(unique_words) / len(words)
            
            # Normalize between 0 and 1, assuming max lex_density of 0.8
            lex_density = min(1.0, lex_density / 0.8)
        else:
            lex_density = 0
        
        # Average sentence length as a complexity factor
        if self.complexity_measure == "sentence_length" or self.complexity_measure == "combined":
            sentences = sent_tokenize(text)
            if not sentences:
                sent_complexity = 0
            else:
                avg_length = sum(len(s) for s in sentences) / len(sentences)
                # Normalize with assumption that 200 char is complex
                sent_complexity = min(1.0, avg_length / 200)
        else:
            sent_complexity = 0
        
        # Combined measure
        if self.complexity_measure == "combined":
            return (lex_density + sent_complexity) / 2
        elif self.complexity_measure == "lexical_density":
            return lex_density
        else:  # sentence_length
            return sent_complexity
    
    def split_text(self, text: str) -> list[str]:
        """Split text into chunks based on adaptive sizing."""
        if not text:
            return []
            
        # First split text into sentences
        sentences = sent_tokenize(text)
        chunks = []
        current_chunk = []
        current_size = 0
        current_complexity = 0.5  # Start with medium complexity
        
        for sentence in sentences:
            sentence_len = self.length_function(sentence)
            
            # Skip empty sentences
            if sentence_len == 0:
                continue
                
            # Analyze sentence complexity
            sentence_complexity = self.analyze_complexity(sentence)
            
            # Update running complexity average
            if current_chunk:
                current_complexity = (current_complexity + sentence_complexity) / 2
            else:
                current_complexity = sentence_complexity
                
            # Calculate target size based on complexity
            # More complex text gets smaller chunks
            target_size = self.max_chunk_size - (current_complexity * (self.max_chunk_size - self.min_chunk_size))
            
            # Calculate adaptive overlap
            target_overlap = self.min_chunk_overlap + (current_complexity * (self.max_chunk_overlap - self.min_chunk_overlap))
            
            # Check if adding this sentence would exceed the target size
            if current_size + sentence_len > target_size and current_chunk:
                # Join current chunk and add to results
                chunks.append(" ".join(current_chunk))
                
                # Start new chunk with overlap
                overlap_size = 0
                overlap_chunk = []
                
                # Add sentences from the end of the previous chunk for overlap
                for prev_sentence in reversed(current_chunk):
                    if overlap_size + self.length_function(prev_sentence) <= target_overlap:
                        overlap_chunk.insert(0, prev_sentence)
                        overlap_size += self.length_function(prev_sentence)
                    else:
                        break
                
                # Start new chunk with the overlap plus the current sentence
                current_chunk = overlap_chunk + [sentence]
                current_size = sum(self.length_function(s) for s in current_chunk)
            else:
                # Add sentence to current chunk
                current_chunk.append(sentence)
                current_size += sentence_len
        
        # Add the last chunk if it exists
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def create_documents(self, texts: list[str], metadatas: list[dict] = None) -> list[Document]:
        """Create Document objects with complexity metadata."""
        documents = []
        
        for i, text in enumerate(texts):
            # Calculate text complexity for metadata
            complexity = self.analyze_complexity(text)
            
            # Create base metadata
            metadata = {
                "chunk_id": i,
                "total_chunks": len(texts),
                "chunk_size": self.length_function(text),
                "chunk_type": "adaptive",
                "text_complexity": round(complexity, 3),
            }
            
            # Add any additional metadata
            if metadatas and i < len(metadatas):
                metadata.update(metadatas[i])
            
            doc = Document(page_content=text, metadata=metadata)
            documents.append(doc)
        
        return documents

def perform_adaptive_chunking(document, min_size=300, max_size=1000, 
                              min_overlap=30, max_overlap=150,
                              complexity_measure="combined"😞
    """
    Performs adaptive chunking on a document, with chunk size varying by text complexity.
    
    Args:
        document (str): The text document to process
        min_size (int): Minimum chunk size for complex sections
        max_size (int): Maximum chunk size for simple sections
        min_overlap (int): Minimum overlap between chunks
        max_overlap (int): Maximum overlap for complex chunks
        complexity_measure (str): Method to measure complexity
        
    Returns:
        list: The adaptively chunked documents with metadata
    """
    # Create the adaptive text splitter
    splitter = AdaptiveTextSplitter(
        min_chunk_size=min_size,
        max_chunk_size=max_size,
        min_chunk_overlap=min_overlap,
        max_chunk_overlap=max_overlap,
        complexity_measure=complexity_measure
    )
    
    # Split the document into chunks
    chunks = splitter.split_text(document)
    print(f"Document split into {len(chunks)} adaptive chunks")
    
    # Create Document objects with complexity metadata
    documents = splitter.create_documents(chunks)
    
    # Add additional metrics
    chunk_sizes = [doc.metadata["chunk_size"] for doc in documents]
    if chunk_sizes:
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        for doc in documents:
            doc.metadata["avg_chunk_size"] = round(avg_size, 1)
            doc.metadata["size_vs_avg"] = round(doc.metadata["chunk_size"] / avg_size, 2)
    
    return documents

# Example usage with Databricks integration
if __name__ == "__main__":
    # Create the dummy document
    document = create_dummy_document()

    # Process with adaptive chunking
    chunked_docs = perform_adaptive_chunking(
        document,
        min_size=300,
        max_size=1000,
        complexity_measure="combined"
    )
    
    # Display results
    print("\n----- CHUNKING RESULTS -----")
    print(f"Total adaptive chunks: {len(chunked_docs)}")
    
    # Calculate complexity stats
    complexities = [doc.metadata["text_complexity"] for doc in chunked_docs]
    sizes = [doc.metadata["chunk_size"] for doc in chunked_docs]
    
    print("\n----- COMPLEXITY ANALYSIS -----")
    print(f"Average complexity: {sum(complexities)/len(complexities):.3f}")
    print(f"Min complexity: {min(complexities):.3f}")
    print(f"Max complexity: {max(complexities):.3f}")
    
    print("\n----- SIZE ANALYSIS -----")
    print(f"Average chunk size: {sum(sizes)/len(sizes):.1f} characters")
    print(f"Min chunk size: {min(sizes)} characters")
    print(f"Max chunk size: {max(sizes)} characters")
    
    # Print examples of high and low complexity chunks
    high_complex_idx = complexities.index(max(complexities))
    low_complex_idx = complexities.index(min(complexities))
    
    print("\n----- HIGHEST COMPLEXITY CHUNK -----")
    print(f"Complexity: {chunked_docs[high_complex_idx].metadata['text_complexity']}")
    print(f"Size: {chunked_docs[high_complex_idx].metadata['chunk_size']} characters")
    print("-" * 40)
    print(chunked_docs[high_complex_idx].page_content[:200] + "...")
    
    print("\n----- LOWEST COMPLEXITY CHUNK -----")
    print(f"Complexity: {chunked_docs[low_complex_idx].metadata['text_complexity']}")
    print(f"Size: {chunked_docs[low_complex_idx].metadata['chunk_size']} characters")
    print("-" * 40)
    print(chunked_docs[low_complex_idx].page_content[:200] + "...")
    
    # For integration with Databricks Vector Search
    print("\nTo integrate with Databricks:")
    print("1. Create embeddings using DatabricksEmbeddings")
    print("2. Store documents and embeddings in a Delta table")
    print("3. Create a Vector Search index with complexity filtering capability")
    print("4. During retrieval, consider filtering by complexity for specific use cases")
Advantages

Dynamically allocates resources to complex sections.
Reduces unnecessary token usage on simpler parts.
Can provide a more nuanced approach to chunking.
Drawbacks

Requires a “complexity” function or metric.
More difficult to debug or tune.
Demands more computation up front.
Best Fit: Mixed-content documents with varying degrees of complexity, such as technical handbooks containing both simple descriptions and advanced in-depth analyses.

5. Context-Enriched Chunking
Concept
Context-enriched methods attach additional metadata or summaries to each chunk. By doing so, retrieval models have more background for each chunk, leading to improved understanding during generation.

Example (using a windowed summarization approach):

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatDatabricks
from langchain_core.documents import Document
import numpy as np

def perform_context_enriched_chunking(document, chunk_size=500, chunk_overlap=50, 
                                     window_size=1, summarize=True😞
    """
    Performs context-enriched chunking by attaching summaries from neighboring chunks.
    
    Args:
        document (str): The text document to process
        chunk_size (int): Base size for each chunk
        chunk_overlap (int): Overlap between chunks
        window_size (int): Number of chunks to include on each side for context
        summarize (bool): Whether to summarize context (True) or use raw text (False)
        
    Returns:
        list: The enriched document chunks with metadata
    """
    # Initialize the Databricks model
    chat_model = ChatDatabricks(
        endpoint="databricks-meta-llama-3-3-70b-instruct",
        temperature=0.1,
        max_tokens=250,
    )

    # Create text splitter with optimal parameters
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    # Split the document into base chunks
    base_chunks = splitter.split_text(document)
    print(f"Document split into {len(base_chunks)} base chunks")

    # Create a summarization chain
    summary_prompt = PromptTemplate.from_template(
        "Provide a brief summary of the following text:\n\n{text}\n\nSummary:"
    )
    summary_chain = LLMChain(llm=chat_model, prompt=summary_prompt)
    combine_documents_chain = StuffDocumentsChain(
        llm_chain=summary_chain,
        document_variable_name="text"
    )

    # Process chunks with contextual windows
    enriched_documents = []
    for i, chunk in enumerate(base_chunks):
        print(f"Processing chunk {i+1}/{len(base_chunks)}")
        
        # Define window around current chunk
        window_start = max(0, i - window_size)
        window_end = min(len(base_chunks), i + window_size + 1)
        window = base_chunks[window_start:window_end]
        
        # Extract context (excluding the current chunk)
        context_chunks = [c for j, c in enumerate(window) if j != i - window_start]
        context_text = " ".join(context_chunks)
        
        # Prepare metadata
        metadata = {
            "chunk_id": i,
            "total_chunks": len(base_chunks),
            "chunk_size": len(chunk),
            "window_start_idx": window_start,
            "window_end_idx": window_end - 1,
            "has_context": len(context_chunks) > 0
        }
        
        # Handle context based on whether summarization is enabled
        if context_chunks and summarize:
            try:
                # Convert to Document objects for the summarization chain
                context_docs = [Document(page_content=context_text)]
                
                # Summarize neighbor chunks for context
                context_summary = combine_documents_chain.invoke(context_docs)
                metadata["context"] = context_summary
                metadata["context_type"] = "summary"
                
                # Create enriched text
                enriched_text = f"Context: {context_summary}\n\nContent: {chunk}"
                
            except Exception as e:
                print(f"Summarization error for chunk {i}: {e}")
                # Fallback to raw context
                metadata["context"] = context_text
                metadata["context_type"] = "raw_text"
                metadata["summary_error"] = str(e)
                enriched_text = f"Context: {context_text}\n\nContent: {chunk}"
        
        elif context_chunks:
            # Use raw context without summarization
            metadata["context"] = context_text
            metadata["context_type"] = "raw_text"
            enriched_text = f"Context: {context_text}\n\nContent: {chunk}"
        
        else:
            # No context available
            metadata["context"] = ""
            metadata["context_type"] = "none"
            enriched_text = chunk
        
        # Create Document object
        doc = Document(
            page_content=enriched_text,
            metadata=metadata
        )
        
        enriched_documents.append(doc)
    
    return enriched_documents

# Mock implementation for testing without Databricks
class MockChatModel:
    """Mock LLM for testing without Databricks."""
    def __init__(self, **kwargs😞
        self.kwargs = kwargs
    
    def invoke(self, input_text😞
        """Generate a simple summary based on the first few words."""
        if isinstance(input_text, list) and hasattr(input_text[0], 'page_content'😞
            text = input_text[0].page_content
        else:
            text = str(input_text)
        
        # Extract first sentence or first 50 characters for mock summary
        first_sentence = text.split('.')[0]
        return f"Summary: {first_sentence[:100]}..."

def perform_context_enriched_chunking_mock(document, chunk_size=500, chunk_overlap=50, 
                                          window_size=1😞
    """
    Mock implementation of context-enriched chunking for testing without Databricks.
    """
    # Create text splitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    # Split the document into base chunks
    base_chunks = splitter.split_text(document)
    print(f"Document split into {len(base_chunks)} base chunks")
    
    # Create a mock summarization function
    def mock_summarize(text😞
        first_sentence = text.split('.')[0]
        return f"Summary: {first_sentence[:100]}..."
    
    # Process chunks with contextual windows
    enriched_documents = []
    for i, chunk in enumerate(base_chunks):
        # Define window around current chunk
        window_start = max(0, i - window_size)
        window_end = min(len(base_chunks), i + window_size + 1)
        window = base_chunks[window_start:window_end]
        
        # Extract context (excluding the current chunk)
        context_chunks = [c for j, c in enumerate(window) if j != i - window_start]
        context_text = " ".join(context_chunks)
        
        # Generate mock summary for context
        if context_chunks:
            context_summary = mock_summarize(context_text)
            metadata = {
                "chunk_id": i,
                "total_chunks": len(base_chunks),
                "context": context_summary,
                "context_type": "summary"
            }
            enriched_text = f"Context: {context_summary}\n\nContent: {chunk}"
        else:
            metadata = {
                "chunk_id": i,
                "total_chunks": len(base_chunks),
                "context": "",
                "context_type": "none"
            }
            enriched_text = chunk
        
        # Create Document object
        doc = Document(
            page_content=enriched_text,
            metadata=metadata
        )
        
        enriched_documents.append(doc)
    
    return enriched_documents

# Example usage
if __name__ == "__main__":

    # Create the dummy document
    document = create_dummy_document()
    
    # Use mock version for testing without Databricks
    print("Using mock implementation for testing...")
    enriched_docs = perform_context_enriched_chunking_mock(
        document,
        chunk_size=500,
        chunk_overlap=50,
        window_size=1
    )
    
    # Display results
    print("\n----- CHUNKING RESULTS -----")
    print(f"Total enriched chunks: {len(enriched_docs)}")
    
    # Print an example chunk with its context
    print("\n----- EXAMPLE ENRICHED CHUNK -----")
    middle_chunk_idx = len(enriched_docs) // 2
    example_chunk = enriched_docs[middle_chunk_idx]
    print(f"Chunk {middle_chunk_idx} with context:")
    print("-" * 40)
    print(example_chunk.page_content)
    print("-" * 40)
    print(f"Metadata: {example_chunk.metadata}")
    
    print("\nTo use with Databricks:")
    print("1. Replace 'perform_context_enriched_chunking_mock' with 'perform_context_enriched_chunking'")
    print("2. Ensure your Databricks endpoint is correctly configured")
    print("3. Store documents with context in Delta table")
    print("4. Create embeddings that include the context information")
Advantages

Helps maintain coherence across different parts of the document.
Can boost retrieval performance in queries that span multiple segments.
Drawbacks

Increases both storage and memory requirements.
Additional preprocessing layer adds complexity.
Can introduce repetitive information if not carefully managed.
Best Fit: Documents where understanding the interplay between sections is crucial (e.g., multi-chapter reports or interconnected research papers).

6. AI-Driven Dynamic Chunking
Concept
AI-based chunking leverages an LLM to detect natural breakpoints in the text, ensuring each chunk encapsulates complete ideas. The approach adjusts chunk size on the fly based on conceptual density.

Example:

from langchain_community.chat_models import ChatDatabricks
from langchain.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json
import re

def perform_ai_driven_chunking(document, max_chunks=20, fallback_chunk_size=1000😞
    """
    Uses an LLM to intelligently chunk content based on semantic boundaries.
    
    Args:
        document (str): The text document to process
        max_chunks (int): Maximum number of chunks to create
        fallback_chunk_size (int): Chunk size to use if LLM chunking fails
        
    Returns:
        list: The semantically chunked documents with metadata
    """
    # Initialize the Databricks LLM
    llm = ChatDatabricks(
        endpoint="databricks-meta-llama-3-3-70b-instruct",
        temperature=0.1,
        max_tokens=4000  # Increased to handle longer outputs
    )
    
    # Create a chat prompt template for the chunking task
    chunking_prompt = ChatPromptTemplate.from_template("""
    You are a document processing expert. Your task is to break down the following document into 
    at most {max_chunks} meaningful chunks. Follow these guidelines:
    
    1. Each chunk should contain complete ideas or concepts
    2. More complex sections should be in smaller chunks
    3. Preserve headers with their associated content
    4. Keep related information together
    5. Maintain the original order of the document
    
    DOCUMENT:
    {document}
    
    Return ONLY a valid JSON array of strings, where each string is a chunk.
    Format your response as:
    ```json
    [
      "chunk1 text",
      "chunk2 text",
      ...
    ]
    ```
    
    Do not include any explanations or additional text outside the JSON array.
    """)
    
    # Create the chain
    chunking_chain = chunking_prompt | llm
    
    try:
        # Invoke the LLM to get chunking suggestions
        response = chunking_chain.invoke({"document": document, "max_chunks": max_chunks})
        
        # Extract JSON from the response
        content = response.content
        
        # Find JSON array in the response (looking for text between [ and ])
        json_match = re.search(r'\[\s*".*"\s*\]', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        
        # Try to parse the JSON response
        chunks = json.loads(content)
        print(f"Successfully chunked document into {len(chunks)} AI-driven chunks")
        
        # Create Document objects with metadata
        documents = []
        for i, chunk in enumerate(chunks):
            # Calculate relative position for tracking
            position = i / len(chunks)
            
            # Analyze chunk complexity based on length and unique word density
            words = re.findall(r'\b\w+\b', chunk.lower())
            unique_words = set(words)
            word_density = len(unique_words) / max(1, len(words))
            
            doc = Document(
                page_content=chunk,
                metadata={
                    "chunk_id": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk),
                    "chunk_type": "ai_driven",
                    "document_position": round(position, 2),
                    "word_count": len(words),
                    "unique_words": len(unique_words),
                    "word_density": round(word_density, 2)
                }
            )
            documents.append(doc)
        
        return documents
            
    except Exception as e:
        print(f"LLM chunking failed: {e}")
        print("Falling back to basic chunking")
        return fallback_chunking(document, chunk_size=fallback_chunk_size)

def fallback_chunking(document, chunk_size=1000, chunk_overlap=100😞
    """
    Fallback method if LLM chunking fails.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = splitter.split_text(document)
    print(f"Fallback chunking created {len(chunks)} chunks")
    
    # Convert to Document objects
    documents = []
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk,
            metadata={
                "chunk_id": i,
                "total_chunks": len(chunks),
                "chunk_size": len(chunk),
                "chunk_type": "fallback",
                "document_position": round(i / len(chunks), 2)
            }
        )
        documents.append(doc)
    
    return documents

# Mock implementation for testing without Databricks
def perform_ai_driven_chunking_mock(document, max_chunks=20😞
    """
    Mock version of AI-driven chunking for testing without Databricks.
    Uses paragraph-based chunking as a simple approximation of LLM chunking.
    """
    # Simple chunking by paragraphs for the mock
    paragraphs = document.split("\n\n")
    
    # Combine very short paragraphs
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if not para.strip():
            continue
            
        if len(current_chunk) + len(para) < 500:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # Ensure we don't exceed max_chunks
    if len(chunks) > max_chunks:
        # Combine chunks to reduce count
        new_chunks = []
        chunks_per_group = len(chunks) // max_chunks + 1
        
        for i in range(0, len(chunks), chunks_per_group):
            group = chunks[i:i + chunks_per_group]
            new_chunks.append("\n\n".join(group))
        
        chunks = new_chunks
    
    print(f"Mock AI chunking created {len(chunks)} chunks")
    
    # Create Document objects
    documents = []
    for i, chunk in enumerate(chunks):
        # Calculate relative position
        position = i / len(chunks)
        
        # Basic text analytics
        words = re.findall(r'\b\w+\b', chunk.lower())
        unique_words = set(words)
        word_density = len(unique_words) / max(1, len(words))
        
        doc = Document(
            page_content=chunk,
            metadata={
                "chunk_id": i,
                "total_chunks": len(chunks),
                "chunk_size": len(chunk),
                "chunk_type": "mock_ai_driven",
                "document_position": round(position, 2),
                "word_count": len(words),
                "unique_words": len(unique_words),
                "word_density": round(word_density, 2)
            }
        )
        documents.append(doc)
    
    return documents

# Example usage
if __name__ == "__main__":
    # Import the dummy document creation function
    
    # Create the dummy document
    document = create_dummy_document()
    
    # Use mock version for testing without Databricks
    print("Using mock implementation for testing...")
    chunked_docs = perform_ai_driven_chunking_mock(document, max_chunks=10)
    
    # Display results
    print("\n----- CHUNKING RESULTS -----")
    print(f"Total chunks: {len(chunked_docs)}")
    
    # Print an example chunk
    print("\n----- EXAMPLE CHUNK -----")
    middle_chunk_idx = len(chunked_docs) // 2
    example_chunk = chunked_docs[middle_chunk_idx]
    print(f"Chunk {middle_chunk_idx}:")
    print("-" * 40)
    print(example_chunk.page_content[:200] + "..." if len(example_chunk.page_content) > 200 
          else example_chunk.page_content)
    print("-" * 40)
    print(f"Metadata: {example_chunk.metadata}")
    
    print("\nTo use with Databricks:")
    print("1. Replace 'perform_ai_driven_chunking_mock' with 'perform_ai_driven_chunking'")
    print("2. Ensure your Databricks endpoint is correctly configured")
    print("3. Consider adjusting max_chunks based on your document size")
Advantages

Highly adaptive, capturing semantic nuance.
Can significantly enhance retrieval accuracy.
Especially useful for complex, multi-topic documents.
Drawbacks

Relies on the performance of the underlying LLM.
Potentially expensive in terms of compute and API calls.
Harder to standardize or replicate consistently.
Best Fit: Projects with generous compute budgets and a critical need for accurate, context-driven chunk segmentation.

Factors to Consider When Choosing a Chunking Strategy
Document Structure & Type
Structured text (reports, articles): Semantic/recursive chunking.
Code or highly technical docs: Recursive, language-specific chunking.
Mixed or unstructured content: AI-driven or context-enriched chunking.
2. Query Complexity

Straightforward, fact-based queries: Smaller, more direct chunks.
Multifaceted, analytical queries: Larger, context-preserving chunks.
Queries spanning multiple concepts: Strategies that keep related data together.
3. Model Constraints

Pay attention to context window sizes of both LLMs and embedding models.
Keep an eye on token usage to avoid excessive costs.
4. Performance Requirements

Latency-sensitive use cases: Lighter, simpler chunking for fast retrieval.
Accuracy-critical domains: More advanced or context-enriched chunking.
Resource-limited settings: Favor straightforward methods like fixed-size or basic semantic splits.
How to Evaluate Chunking Approaches
Quantitative Metrics
Context Precision: How precisely do the chunks contain relevant info without adding unnecessary data?
Context Recall: How fully do the chunks capture all critical info for a query?
Processing Efficiency: How quickly can chunks be generated and retrieved?
Resource Utilization: CPU, memory, and storage overhead.
Sample Evaluation Framework
import time
import pandas as pd
import matplotlib.pyplot as plt
import re
from collections import Counter


def calculate_keyword_coverage(chunks, keywords😞
    """
    Calculate what percentage of keywords appear in at least one chunk.
    
    Args:
        chunks (list): List of text chunks
        keywords (list): List of keywords to search for
        
    Returns:
        float: Percentage of keywords covered (0-1)
    """
    # Convert chunks to lowercase for case-insensitive matching
    lowercase_chunks = [chunk.lower() for chunk in chunks]
    lowercase_keywords = [keyword.lower() for keyword in keywords]
    
    # Count how many keywords appear in at least one chunk
    keywords_found = 0
    for keyword in lowercase_keywords:
        if any(keyword in chunk for chunk in lowercase_chunks):
            keywords_found += 1
    
    # Calculate coverage
    coverage = keywords_found / max(1, len(keywords))
    return coverage

def calculate_chunk_coherence(chunks😞
    """
    Calculate the average coherence of chunks based on sentence completeness.
    
    Args:
        chunks (list): List of text chunks
        
    Returns:
        float: Coherence score (0-1)
    """
    # Count incomplete sentences at chunk boundaries
    incomplete_boundaries = 0
    
    for chunk in chunks:
        # Check if chunk starts with lowercase letter or continuation punctuation
        if chunk and (chunk[0].islower() or chunk[0] in ',;:)]}'😞
            incomplete_boundaries += 1
        
        # Check if chunk ends without proper sentence-ending punctuation
        if chunk and not re.search(r'[.!?]\s*$', chunk):
            incomplete_boundaries += 1
    
    # Calculate coherence (lower incomplete_boundaries = higher coherence)
    max_boundaries = len(chunks) * 2  # Start and end of each chunk
    coherence = 1 - (incomplete_boundaries / max(1, max_boundaries))
    return coherence

def calculate_concept_splitting(chunks, key_phrases😞
    """
    Calculate how often key phrases are split across chunks.
    
    Args:
        chunks (list): List of text chunks
        key_phrases (list): List of important phrases that should stay together
        
    Returns:
        float: Non-splitting score (0-1), higher is better
    """
    # Count how many key phrases are split
    split_phrases = 0
    
    for phrase in key_phrases:
        phrase_lower = phrase.lower()
        
        # Check if phrase appears completely in any chunk
        complete_in_chunk = any(phrase_lower in chunk.lower() for chunk in chunks)
        
        # Check if parts of the phrase appear in different chunks
        words = phrase_lower.split()
        if len(words) > 1:
            parts_in_different_chunks = False
            
            for i in range(len(words) - 1😞
                part1 = " ".join(words[:i+1])
                part2 = " ".join(words[i+1:])
                
                for j, chunk1 in enumerate(chunks):
                    if part1 in chunk1.lower():
                        for chunk2 in chunks[j+1:]:
                            if part2 in chunk2.lower() and part1 not in chunk2.lower():
                                parts_in_different_chunks = True
                                break
            
            if parts_in_different_chunks and not complete_in_chunk:
                split_phrases += 1
    
    # Calculate non-splitting score
    non_splitting = 1 - (split_phrases / max(1, len(key_phrases)))
    return non_splitting

def evaluate_chunking_strategies(document, keywords, key_phrases, chunking_strategies😞
    """
    Evaluates chunking strategies with custom metrics.
    
    Args:
        document (str): Document to chunk
        keywords (list): Important keywords for coverage metric
        key_phrases (list): Important phrases for concept splitting metric
        chunking_strategies (dict): Dictionary of chunking strategies with parameters
        
    Returns:
        pd.DataFrame: Results of the evaluation
    """
    results = []
    
    for name, strategy in chunking_strategies.items():
        print(f"Evaluating strategy: {name}")
        start_time = time.time()
        
        # Perform chunking based on strategy type
        if strategy["type"] == "fixed":
            chunks = perform_fixed_size_chunking(
                document, 
                chunk_size=strategy.get("size", 1000),
                chunk_overlap=strategy.get("overlap", 0)
            )
        elif strategy["type"] == "semantic":
            chunks = perform_semantic_chunking(
                document,
                chunk_size=strategy.get("size", 500),
                chunk_overlap=strategy.get("overlap", 100)
            )
        elif strategy["type"] == "recursive":
            chunks = perform_code_chunking(
                document,
                language=strategy.get("language", "python"),
                chunk_size=strategy.get("size", 100),
                chunk_overlap=strategy.get("overlap", 15)
            )
        elif strategy["type"] == "adaptive":
            chunks = perform_adaptive_chunking(
                document,
                min_size=strategy.get("min_size", 300),
                max_size=strategy.get("max_size", 1000),
                complexity_measure=strategy.get("complexity_measure", "combined")
            )
        elif strategy["type"] == "context_enriched":
            chunks = perform_context_enriched_chunking(
                document,
                chunk_size=strategy.get("size", 500),
                chunk_overlap=strategy.get("overlap", 50),
                window_size=strategy.get("window_size", 1)
            )
        elif strategy["type"] == "ai_driven":
            chunks = perform_ai_driven_chunking(
                document,
                max_chunks=strategy.get("max_chunks", 10)
            )
        else:
            raise ValueError(f"Unknown chunking strategy type: {strategy['type']}")
        
        # Record processing time
        processing_time = time.time() - start_time
        
        # Convert to text for evaluation if they're Document objects
        chunk_texts = []
        for chunk in chunks:
            if hasattr(chunk, 'page_content'😞
                chunk_texts.append(chunk.page_content)
            else:
                chunk_texts.append(chunk)
        
        # Calculate custom metrics
        keyword_coverage = calculate_keyword_coverage(chunk_texts, keywords)
        chunk_coherence = calculate_chunk_coherence(chunk_texts)
        concept_integrity = calculate_concept_splitting(chunk_texts, key_phrases)
        
        # Calculate chunk statistics
        total_chunks = len(chunks)
        
        # Get chunk sizes
        if hasattr(chunks[0], 'page_content'😞
            chunk_sizes = [len(chunk.page_content) for chunk in chunks]
        else:
            chunk_sizes = [len(chunk) for chunk in chunks]
            
        avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)
        chunk_size_std = (sum((size - avg_chunk_size) ** 2 for size in chunk_sizes) / len(chunk_sizes)) ** 0.5
        size_consistency = 1 - (chunk_size_std / max(1, avg_chunk_size))
        
        # Store results
        results.append({
            "strategy": name,
            "processing_time": round(processing_time, 2),
            "keyword_coverage": round(keyword_coverage, 2),
            "chunk_coherence": round(chunk_coherence, 2),
            "concept_integrity": round(concept_integrity, 2),
            "size_consistency": round(size_consistency, 2),
            "total_chunks": total_chunks,
            "avg_chunk_size": round(avg_chunk_size, 2)
        })
    
    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    return results_df

def visualize_results(results_df😞
    """
    Creates visualizations of the evaluation results.
    
    Args:
        results_df (pd.DataFrame): Evaluation results
    """
    # Set up the figure
    fig, axs = plt.subplots(2, 3, figsize=(18, 12))
    
    # Plot processing time
    axs[0, 0].bar(results_df['strategy'], results_df['processing_time'])
    axs[0, 0].set_title('Processing Time (seconds)')
    axs[0, 0].set_ylabel('Time (s)')
    axs[0, 0].set_xticklabels(results_df['strategy'], rotation=45, ha='right')
    
    # Plot quality metrics
    axs[0, 1].bar(results_df['strategy'], results_df['keyword_coverage'])
    axs[0, 1].set_title('Keyword Coverage')
    axs[0, 1].set_ylabel('Score (0-1)')
    axs[0, 1].set_xticklabels(results_df['strategy'], rotation=45, ha='right')
    
    # Plot concept integrity
    axs[0, 2].bar(results_df['strategy'], results_df['concept_integrity'])
    axs[0, 2].set_title('Concept Integrity')
    axs[0, 2].set_ylabel('Score (0-1)')
    axs[0, 2].set_xticklabels(results_df['strategy'], rotation=45, ha='right')
    
    # Plot chunk coherence
    axs[1, 0].bar(results_df['strategy'], results_df['chunk_coherence'])
    axs[1, 0].set_title('Chunk Coherence')
    axs[1, 0].set_ylabel('Score (0-1)')
    axs[1, 0].set_xticklabels(results_df['strategy'], rotation=45, ha='right')
    
    # Plot total chunks
    axs[1, 1].bar(results_df['strategy'], results_df['total_chunks'])
    axs[1, 1].set_title('Total Number of Chunks')
    axs[1, 1].set_ylabel('Count')
    axs[1, 1].set_xticklabels(results_df['strategy'], rotation=45, ha='right')
    
    # Plot size consistency
    axs[1, 2].bar(results_df['strategy'], results_df['size_consistency'])
    axs[1, 2].set_title('Chunk Size Consistency')
    axs[1, 2].set_ylabel('Score (0-1)')
    axs[1, 2].set_xticklabels(results_df['strategy'], rotation=45, ha='right')
    
    plt.tight_layout()
    plt.show()

# Example usage
if __name__ == "__main__":
    # Create test document
    document = create_dummy_document()
    
    # Define important keywords for evaluation
    keywords = [
        "machine learning", "supervised learning", "unsupervised learning", 
        "neural networks", "LLMs", "fine-tuning", "pre-training",
        "reinforcement learning", "multimodal learning", "federated learning",
        "clustering", "classification", "regression", "PCA"
    ]
    
    # Define key phrases that should remain together
    key_phrases = [
        "Large Language Models",
        "Reinforcement Learning from Human Feedback",
        "Principal Component Analysis",
        "Support Vector Machines",
        "decision becomes more difficult",
        "train-test split",
        "natural language processing"
    ]
    
    # Define chunking strategies to evaluate
    chunking_strategies = {
        "fixed_500": {
            "type": "fixed", 
            "size": 500, 
            "overlap": 0
        },
        "fixed_500_overlap_100": {
            "type": "fixed", 
            "size": 500, 
            "overlap": 100
        },
        "semantic_500": {
            "type": "semantic", 
            "size": 500, 
            "overlap": 100
        },
        "adaptive_300_1000": {
            "type": "adaptive", 
            "min_size": 300, 
            "max_size": 1000,
            "complexity_measure": "combined"
        },
        "context_enriched_500": {
            "type": "context_enriched", 
            "size": 500, 
            "overlap": 50,
            "window_size": 1
        },
        "ai_driven_10": {
            "type": "ai_driven", 
            "max_chunks": 10
        }
    }
    
    # Run evaluation
    results_df = evaluate_chunking_strategies(document, keywords, key_phrases, chunking_strategies)
    
    # Print results
    print("\n----- EVALUATION RESULTS -----")
    print(results_df)
    
    # Create visualizations
    try:
        visualize_results(results_df)
    except Exception as e:
        print(f"Visualization error: {e}")
    
    # Export results to CSV
    results_df.to_csv("chunking_evaluation_results.csv", index=False)
    print("\nResults exported to 'chunking_evaluation_results.csv'")
A study from MongoDB suggests that when handling Python documentation, a language-specific recursive splitter (chunk size of ~100 tokens and overlap of ~15 tokens) often yields the best combination of context precision and recall.

Best Practices & Implementation Guidelines
Begin with Baseline Testing
Start simple (e.g., fixed-size chunking with different chunk and overlap sizes). Gather metrics to establish a reference point before introducing complexity.
from langchain_text_splitters import CharacterTextSplitter

def perform_baseline_testing(document😞
    """Test different chunk sizes and overlaps to establish a baseline."""
    test_sizes = [100, 200, 500, 1000]
    results = []
    
    for size in test_sizes:
        splitter = CharacterTextSplitter(
            chunk_size=size,
            chunk_overlap=int(size * 0.2),
            separator="\n\n"
        )
        
        chunks = splitter.split_text(document)
        
        results.append({
            "chunk_size": size,
            "overlap": int(size * 0.2),
            "num_chunks": len(chunks),
            "avg_chunk_length": sum(len(c) for c in chunks) / len(chunks)
        })
        
    return results
2. Optimize Chunk Size & Overlap

General text: 200–500 tokens, 10–20% overlap.
Code or very technical content: 100–200 tokens, 15–25% overlap.
Narrative content: 500–1000 tokens to preserve context.
from langchain_text_splitters import RecursiveCharacterTextSplitter

def optimize_chunking_by_content_type(document, content_type😞
    """Apply optimized chunking based on content type."""
    if content_type == "general":
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=60,  # ~15% overlap
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    elif content_type == "technical":
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=150,
            chunk_overlap=30,  # ~20% overlap
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    elif content_type == "narrative":
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,  # ~12.5% overlap
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    return splitter.split_text(document)
3. Use Hybrid Methods Where Appropriate
If a single document includes standard text, tables, and code, treat each section with a suitable approach.

from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
import re

def hybrid_chunking(document😞
    """Process different sections of a document with appropriate methods."""
    # Detect section types (simplified example)
    sections = []
    current_section = {"type": "text", "content": ""}
    
    for line in document.split('\n'😞
        if re.match(r'```python|```js|```java', line):
            # Start a new code section
            if current_section["content"]:
                sections.append(current_section)
            current_section = {"type": "code", "language": line.strip('`'), "content": ""}
        elif re.match(r'```', line) and current_section["type"] == "code":
            # End code section
            if current_section["content"]:
                sections.append(current_section)
            current_section = {"type": "text", "content": ""}
        elif re.match(r'\|.*\|.*\|', line):
            # Likely a markdown table
            if current_section["type"] != "table":
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {"type": "table", "content": line + "\n"}
            else:
                current_section["content"] += line + "\n"
        else:
            current_section["content"] += line + "\n"
    
    # Add the last section
    if current_section["content"]:
        sections.append(current_section)
    
    # Process each section with appropriate chunker
    chunks = []
    for section in sections:
        if section["type"] == "code":
            code_splitter = RecursiveCharacterTextSplitter.from_language(
                language=Language.PYTHON,  # Simplified, should match actual language
                chunk_size=100,
                chunk_overlap=20
            )
            section_chunks = code_splitter.split_text(section["content"])
        elif section["type"] == "table":
            # Special handling for tables - keep them intact
            section_chunks = [section["content"]]
        else:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=400,
                chunk_overlap=50,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            section_chunks = text_splitter.split_text(section["content"])
        
        # Add metadata about section type
        for i, chunk in enumerate(section_chunks):
            chunks.append({
                "content": chunk,
                "type": section["type"],
                "index": i,
                "total": len(section_chunks)
            })
    
    return chunks
4. Add Metadata to Chunks
Storing metadata (e.g., section title, document type, date) helps with filtering and contextual retrieval.

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import re

def chunks_with_metadata(document, title, document_type, date😞
    """Create chunks with rich metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    
    # Extract headings for better section tracking
    headings = {}
    current_position = 0
    for match in re.finditer(r'(#{1,6})\s+(.*?)\s*$', document, re.MULTILINE):
        heading_level = len(match.group(1))
        heading_text = match.group(2)
        headings[match.start()] = {
            "level": heading_level,
            "text": heading_text
        }
    
    # Create basic chunks first
    text_chunks = splitter.split_text(document)
    
    # Convert to Document objects with metadata
    doc_chunks = []
    for i, chunk in enumerate(text_chunks):
        # Find the most recent heading before this chunk
        chunk_start_pos = document.find(chunk)
        current_heading = None
        for pos, heading in sorted(headings.items()):
            if pos <= chunk_start_pos:
                current_heading = heading
            else:
                break
        
        # Create metadata
        metadata = {
            "chunk_id": i,
            "document_title": title,
            "document_type": document_type,
            "date": date,
            "total_chunks": len(text_chunks)
        }
        
        # Add section information if available
        if current_heading:
            metadata["section"] = current_heading["text"]
            metadata["section_level"] = current_heading["level"]
        
        # Create Document object
        doc = Document(page_content=chunk, metadata=metadata)
        doc_chunks.append(doc)
    
    return doc_chunks
5. Preserve Semantic Boundaries
Avoid prematurely cutting in the middle of a sentence or important paragraph.

import nltk
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Download NLTK data if not already available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

def semantic_boundary_chunking(document, target_size=500😞
    """Create chunks that respect sentence boundaries."""
    # First tokenize into sentences
    sentences = nltk.sent_tokenize(document)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence_len = len(sentence)
        
        # If adding this sentence would exceed target size and we already have content
        if current_size + sentence_len > target_size and current_chunk:
            # Join current sentences and add to chunks
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
            current_size = sentence_len
        else:
            current_chunk.append(sentence)
            current_size += sentence_len
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks
6. Handle Structured Content Separately
For documents that include images, tables, or code blocks, combine specialized processing logic with your chunking approach.

def process_structured_content(document😞
    """Handle different types of structured content."""
    import re
    from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
    
    # Define pattern for various structured content
    patterns = {
        "table": r'\|.*\|.*\|[\s\S]*?\n\n',
        "code_block": r'```[\s\S]*?```',
        "image": r'!\[.*?\]\(.*?\)'
    }
    
    # Extract structured content and replace with placeholders
    structured_parts = {}
    placeholder_count = 0
    modified_document = document
    
    for content_type, pattern in patterns.items():
        matches = re.finditer(pattern, document, re.MULTILINE)
        for match in matches:
            placeholder = f"[PLACEHOLDER_{placeholder_count}]"
            placeholder_count += 1
            structured_parts[placeholder] = {
                "type": content_type,
                "content": match.group(0)
            }
            modified_document = modified_document.replace(match.group(0), placeholder)
    
    # Chunk the modified document
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    base_chunks = text_splitter.split_text(modified_document)
    
    # Replace placeholders and process structured content appropriately
    final_chunks = []
    for chunk in base_chunks:
        current_chunk = chunk
        for placeholder, content_data in structured_parts.items():
            if placeholder in chunk:
                if content_data["type"] == "code_block":
                    # Keep code blocks intact
                    code_content = content_data["content"]
                    current_chunk = current_chunk.replace(placeholder, code_content)
                elif content_data["type"] == "table":
                    # Keep tables intact
                    table_content = content_data["content"]
                    current_chunk = current_chunk.replace(placeholder, table_content)
                elif content_data["type"] == "image":
                    # Replace image references with metadata
                    image_ref = content_data["content"]
                    image_alt = re.search(r'!\[(.*?)\]', image_ref)
                    alt_text = image_alt.group(1) if image_alt else "image"
                    current_chunk = current_chunk.replace(
                        placeholder, f"[Image description: {alt_text}]"
                    )
        
        final_chunks.append(current_chunk)
    
    return final_chunks
7. Continuous Feedback & Refinement
Maintain a feedback loop using real-world queries and user interactions. Refine chunking configurations based on what chunks are retrieved and how effectively they answer questions.

def evaluate_chunking_performance(queries, retrieved_chunks, user_ratings😞
    """Analyze and refine chunking based on user feedback."""
    
    chunk_effectiveness = {}
    
    # Analyze which chunks were most useful for which queries
    for query, chunks, rating in zip(queries, retrieved_chunks, user_ratings):
        for chunk in chunks:
            chunk_id = chunk.metadata.get("chunk_id", "unknown")
            
            if chunk_id not in chunk_effectiveness:
                chunk_effectiveness[chunk_id] = {
                    "query_count": 0,
                    "total_rating": 0,
                    "queries": []
                }
            
            chunk_effectiveness[chunk_id]["query_count"] += 1
            chunk_effectiveness[chunk_id]["total_rating"] += rating
            chunk_effectiveness[chunk_id]["queries"].append(query)
    
    # Calculate average ratings and identify patterns
    refinement_suggestions = []
    
    for chunk_id, stats in chunk_effectiveness.items():
        if stats["query_count"] > 0:
            avg_rating = stats["total_rating"] / stats["query_count"]
            
            # Analyze low-performing chunks
            if avg_rating < 3:  # Assuming 1-5 rating scale
                refinement_suggestions.append({
                    "chunk_id": chunk_id,
                    "avg_rating": avg_rating,
                    "issue": "Low performance across queries",
                    "suggestion": "Consider refining this chunk or checking content quality"
                })
            
            # Look for content type patterns
            query_keywords = " ".join(stats["queries"]).lower()
            if "code" in query_keywords and avg_rating < 4:
                refinement_suggestions.append({
                    "chunk_id": chunk_id,
                    "avg_rating": avg_rating,
                    "issue": "Poor performance on code-related queries",
                    "suggestion": "Use code-specific chunking for this section"
                })
    
    return refinement_suggestions
Advanced Techniques & Emerging Trends
Domain-Specific Chunking
Legal, medical, or financial documents often have domain-specific layouts (e.g., legal “clauses” or medical “sections”). Tailor chunking to each domain’s conventions.
Multi-Modal Chunking
If you have images, tables, and text in the same source, convert each into a textual or descriptive format that your model can handle, possibly using an LLM to generate textual summaries of non-text elements.
Dynamic Query-Aware Chunking
Adjust chunk sizes or selection dynamically based on query patterns or user context. For instance, small precise chunks might be ideal for straightforward factual queries, while broader semantic chunks might benefit exploratory or conceptually complex questions.
Neural Chunking Models
Specialized neural models can learn to predict optimal chunk boundaries. These advanced classifiers can balance semantic coherence and chunk length better than rule-based methods.
Hierarchical Chunking
Build multi-level chunk hierarchies that preserve document structure (e.g., major sections, subsections, paragraphs). This can be particularly useful when dealing with lengthy or multi-layered texts.
Conclusion
An effective chunking strategy is vital for any RAG system, as it directly impacts how documents are segmented and retrieved. The best approach depends on your specific domain, data structure, and performance needs. The key takeaways:

There’s No Universal Strategy: Each method — from fixed-size to AI-driven dynamic chunking — has trade-offs. Experiment to see what works best.
Balance Size and Semantics: Strive to keep chunks large enough for meaningful context but small enough to remain computationally efficient.
Preserve Context: Break text at natural boundaries when possible, and consider adding contextual metadata for better retrieval.
Iterate Continuously: Always monitor real-world retrieval performance and refine your chunking strategies as your application evolves.
Hybrid Approaches Excel: When in doubt, mix and match strategies to handle different content types optimally.
##############