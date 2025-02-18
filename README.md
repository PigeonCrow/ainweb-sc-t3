# AInWeb task3 Server-Client-Channel

# Channel Name: Tell Tale Channel

## Purpose

It receives messages from multiple users, displays said messages and analyses the overall conversational coherence.

## Filter

To somehow have a form of moderation, the package `better-profanity`
is used.

***Import***

`from better_profanity import profanity`

***Function to Filter messages***

```python
def filter_message(message):
    censored_message = profanity.censor(message)

    return censored_message
```

## Coherence verification

During implementation the focus was set on simplicity, nontheless to achive better results multiple approaches were explored.

### 1. Text mining for basic analisis with TF-IDF

One approach to verify contextual coherence would be to check for literal simmilarity.
Using the sklearn package we can use TfidfVectorizer to encode the text 
and with cosine_similarity check litteral divergences in the conversation. 

***Import***

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

```

***Function implementation***

0. messages are filtered by user content 
    
    0.1. If there is no user content then coherence is 100%
    
1. text is encoded

2. similarity calculated

3. similarity factor converted into percentage( multiply by 100) and returned


```python
def calc_similarity(new_message, messages):

    # filter user content directly
    user_content = [
        msg["content"] for msg in messages if msg["sender"].lower() != "system"
    ]

    if not user_content:
        return 100


    updated_convo = user_content + [new_message]

    # transform messages
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(updated_convo)

    # calculate cosine similarity, to have an approach of coherence
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]


    # return a percentage value
    similarity_percentage = similarity * 100

    return similarity_percentage

```

One issue noted, is that the similarity calculated is much literal and less semantical, 
this approach is/was sometimes used to verify plagiarism. The similarity factor fluctuates and can be hightend by using repetitions.

### 2. Local sentence transformer

Another more efficient method to verify semantical similarity, is using a transformer, given one has the resoureces.
In this case for a functional local implementation `paraphrase-MiniLM-L6-v2` was used, a sentence transformer model with a pretrained BERT encoder (https://huggingface.co/sentence-transformers/paraphrase-MiniLM-L6-v2) 

***Import and loading correct model***

```python
from sentence_transformers import SentenceTransformer, util

semantic_model = SentenceTransformer("paraphrase-MiniLM-L6-v2")

```

***Function implementation***

0. Filter for user content
    0.1 return full coherence if no content 
1. encode in embedding space for transformer
2. calculated cosine similarity
3. return percentage

```python
def calc_similarity(new_message, messages):


    # filter user content directly
    user_content = [
        msg["content"] for msg in messages if msg["sender"].lower() != "system"
    ]

    # return 100% for first message
    if not user_content:
        return 100


    updated_convo = user_content + [new_message]


    # encode using transformer
    embeddings = semantic_model.encode(updated_convo)


    # calculate similaritiy using transformer
    similarity = util.cos_sim(embeddings[-2], embeddings[-1]).item()


    # return a percentage value
    # similarity_percentage = similarity * 100

    return similarity_percentage

```

This is more suitable/robust for actual semmantic similarity. It runs locally, takes up some resources.

### 3. Openai key

To fulfill the original requirement only a calculated value is needed, 
however to avoid heavy resource consumption on the server, an Openai Key is ultimatly used.

***Import***

```python
import openai
```

***function definition***

in this case since only the updated conversation is passed, and an evaluation is requested, no encoding or calculation needed.
Also prompt can be more elaborate in requestinig specific commentary.
The returned similarity_percentage is no longer a value but the full response.

```python
def calc_similarity(new_message, messages):

    user_content = [
        msg["content"] for msg in messages if msg["sender"].lower() != "system"
    ]

     if not user_content:
        return 100

    updated_convo = user_content + [new_message]
  
    # block all msgs with carrige return
    convo_block = "\n".join(updated_convo)

    # Construct the prompt for the AI
    prompt_messages = [
        {
            "role": "system",
            "content": (
                "you are a judge that evaluates the overall coherence of a conversation. "
                "given the conversation below, provide an overall coherence score from 0 to 100. "
                "0 means completely incoherent and 100 means perfectly coherent. "
                "also, include a brief comment with your evaluation. "
                "format your response as: 'Overall coherence: XX% - your comment ...'."
                "if the coherence is above 50, your comment should be possitive, "
                "above 70, your comment should be very lauding, almost extactic, "
                "between 30 and 50, comment should be neutral possitive, "
                "if the coherence is below 30, your comment should be negative, "
                "and below 20, should be almost dramatic. "
            ),
        },
        {
            "role": "user",
            "content": f"Conversation:\n{convo_block}\n\nPlease evaluate the overall coherence of the conversation.",
        },
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4", messages=prompt_messages, temperature=0.5
    )

    # extract and return the coherence evaluation from the assistant's response
    similarity_percentage = response["choices"][0]["message"]["content"].strip()


    return similarity_percentage

```


