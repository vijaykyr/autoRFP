#Class - instantiate with csv of Q and As
#Method - given Q output A

import pandas as pd
import nltk
import string
from datetime import datetime
from gensim import similarities
from gensim import models
from gensim import corpora


#Define Class Constants
FILE_NAME = 'RFX01-10172016.csv'
STEMMER = nltk.stem.snowball.SnowballStemmer("english")
#ToDo: Consider moving stopwords to external file 
STOPWORDS = [u'i', u'me', u'my', u'myself', u'we', u'our', u'ours', u'ourselves', u'you', u'your', u'yours',
 u'yourself', u'yourselves', u'he', u'him', u'his', u'himself', u'she', u'her', u'hers', u'herself', u'it', u'its',
 u'itself', u'they', u'them', u'their', u'theirs', u'themselves', u'what', u'which', u'who', u'whom', u'this', u'that',
 u'these', u'those', u'am', u'is', u'are', u'was', u'were', u'be', u'been', u'being', u'have', u'has', u'had',
 u'having', u'do', u'does', u'did', u'doing', u'a', u'an', u'the', u'and', u'but', u'if', u'or', u'because', u'as', 
 u'until', u'while', u'of', u'at', u'by', u'for', u'with', u'about', u'against', u'between', u'into', u'through',
 u'during', u'before', u'after', u'above', u'below', u'to', u'from', u'up', u'down', u'in', u'out', u'on', u'off',
 u'over', u'under', u'again', u'further', u'then', u'once', u'here', u'there', u'when', u'where', u'why', u'how',
 u'all', u'any', u'both', u'each', u'few', u'more', u'most', u'other', u'some', u'such', u'no', u'nor', u'not', u'only',
 u'own', u'same', u'so', u'than', u'too', u'very', u's', u't', u'can', u'will', u'just', u'don', u'should', u'now',
 u'd', u'll', u'm', u'o', u're', u've', u'y', u'ain', u'aren', u'couldn', u'didn', u'doesn', u'hadn', u'hasn', u'haven',
 u'isn', u'ma', u'mightn', u'mustn', u'needn', u'shan', u'shouldn', u'wasn', u'weren', u'won', u'wouldn']

#Functions
def normalize(text):
    if(type(text) == unicode): text = text.encode('ascii','ignore') 
    #the translate function doesn't work on unicode
    text = unicode(text.lower().translate(None, string.punctuation),errors='replace')
    #encoding back to unicode for NLTK compatibility
    text = [word for word in text.split() if word not in STOPWORDS]
    text = [STEMMER.stem(word) for word in text]
    return text

#Score from 0 to 1 
#  0: >= MAX_DAYS
#  1: today
#Assumption: date is passed as string in format "YYYY-MM-DD"
def get_freshness_score(date):
  MAX_DAYS = 365.0 
  #Convert string to date
  date = datetime.strptime(date , '%Y-%m-%d').date()
  #Calculate from since today
  days_past = (datetime.now().date() - date).days
  #if the date is in the future assume it's corrupt, set to max
  if days_past < 0 or days_past > MAX_DAYS: days_past = MAX_DAYS
  #scale from 0 to 1, round and return
  return round((MAX_DAYS-days_past)/MAX_DAYS,2)
  
  
def get_answers(questions,number_of_answers):
  questions = filter(None,questions) #remove empty lines
  questions_normalized = [normalize(question) for question in questions]
  questions_bow = [dictionary.doc2bow(question_normalized) for question_normalized in questions_normalized]
  questions_tfidf = [tfidf[question_bow] for question_bow in questions_bow]

  i=0
  
  answers = []
  for question_tfidf in questions_tfidf:
    #similarity_scores = index_tfidf[question_tfidf]
    #freshness_score = [get_freshness_score(item.get("date")) for item in data]
    sims = sorted(enumerate(index_tfidf[question_tfidf]), key=lambda item: -item[1])[:number_of_answers]
    possible_answers = [{
      "answer":data.loc[sim[0]],
      "similarity_score":round(sim[1],2),
    } for sim in sims]  
    answers.append({"question":questions[i],"answers":possible_answers})
    i=i+1
      
  return answers

#INITIALIZE CLASS
          
#Load data
#ToDO: Load this from cloud SQL
data = pd.read_csv(FILE_NAME)
#add freshness score
data['freshness_score']=data.apply(lambda row: get_freshness_score(row['date']), axis=1)

#Extract questions column as list
documents = data['question'].tolist()

#Normalize
corpus = [normalize(text) for text in documents]

#Build corpus dictionary
dictionary = corpora.Dictionary(corpus)

#Vectorize
corpus_bow = [dictionary.doc2bow(text) for text in corpus]
tfidf = models.TfidfModel(corpus_bow)
corpus_tfidf = tfidf[corpus_bow]

#Generate similiarity index
index_tfidf = similarities.MatrixSimilarity(corpus_tfidf)

print("TFIDF Index created!")

