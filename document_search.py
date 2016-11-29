#Class - instantiate with csv of Q and As
#Method - given Q output A

import os
import sys
import config
import threading
from time import sleep
import pandas as pd
import nltk
import string
from datetime import datetime
from gensim import similarities
from gensim import models
from gensim import corpora
import mysql.connector

#Define Class Constants
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

#GLOBALS
lock = threading.Lock() #Lock to update globals
data_G = [] #Pandas DataFrame containing corpus
dictionary_G = [] #List of unique words in the corpus
tfidf_G = [] #Frequency of each word in the corpus
index_tfidf_G = [] #Index for fast tfidf comparisons

#Thread to periodically check Cloud SQL for updates
class updateThread (threading.Thread):
  def run(self):
    last_update_time = sql_query("""SELECT update_time FROM information_schema.tables 
          WHERE table_schema='{}' AND table_name='{}'""".format(config.MYSQL_DATABASE, config.MYSQL_TABLE))
    
    while(True):
      sleep(3600) 
      print("Checking Cloud SQL for updates.")
      current_update_time = sql_query("""SELECT update_time FROM information_schema.tables 
          WHERE table_schema='{}' AND table_name='{}'""".format(config.MYSQL_DATABASE, config.MYSQL_TABLE))
      #if query returned and table update time has changed
      if current_update_time and (current_update_time != last_update_time):
        last_update_time = current_update_time
        initialize()
        print("Index updated from Cloud SQL.")
      elif current_update_time: print("No update from Cloud SQL needed.")

#Functions

#Normalize text: lowercase, strip punctation, remove stopwords, stem
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
  
  
def get_answers(questions,number_of_answers,min_sim):
  #Fetch globals
  with lock:
    dictionary = dictionary_G
    tfidf = tfidf_G
    index_tfidf = index_tfidf_G
    data = data_G
    
  #Calculate TF-IDF vector representation(s) of input question(s)
  questions = filter(None,questions) #remove empty lines
  questions_normalized = [normalize(question) for question in questions]
  questions_bow = [dictionary.doc2bow(question_normalized) for question_normalized in questions_normalized]
  questions_tfidf = [tfidf[question_bow] for question_bow in questions_bow]

  i=0
  answers = []
  for question_tfidf in questions_tfidf:
    #generate list of tuples of form (answer index, similartity score)
    scores = list(enumerate(index_tfidf[question_tfidf]))
    #filter out answers not meeting minimum similarity score
    scores = [elem for elem in scores if elem[1] >= min_sim]
    #calcuate overall score and add to tuple: (answer index, similartity score, overall score)
    scores = [score + ((2./3)*score[1] + (1./3)*data.loc[score[0]].get("freshness_score"),) for score in scores]
        
    #Sort and extract top scores    
    top_scores = sorted(scores, key=lambda item: -item[2])[:number_of_answers]
    
    possible_answers = [{
      "answer":data.loc[score[0]],
      "similarity_score":round(score[1],2),
      "overall_score":round(score[2],2)
    } for score in top_scores]  
    answers.append({"question":questions[i],"answers":possible_answers})
    i=i+1
      
  return answers

#Fetch corpus from Cloud SQL database
def sql_query(query):
  ####START Load Data from Cloud SQL####

  #establish connection
  try:
    if os.environ.get('GAE_INSTANCE'): #app engine
        cnx = mysql.connector.connect(user=config.MYSQL_USER, password=config.MYSQL_PASSWORD,
                                      database=config.MYSQL_DATABASE, 
                                      unix_socket=os.environ.get('SQL_CONNECTION_STRING'))
    else: #local
        cnx = mysql.connector.connect(user=config.MYSQL_USER, password=config.MYSQL_PASSWORD,
                                      host=config.MYSQL_HOST, database=config.MYSQL_DATABASE)

    #cursor object required for queries
    cursor = cnx.cursor()

    #execute query, results are stored in cursor object
    cursor.execute((query))
    cnx.close()
  
    #List of tuples. where each tuple is a row
    return cursor.fetchall()
  except:
    sys.stderr.write("ERROR: Failed to connect to mySQL. Check that database is up.\n")
  
#Download Corpus, normalize, and vectorize
def initialize():          
  global dictionary_G, tfidf_G, index_tfidf_G, data_G
  
  #Fetch data
  data = sql_query("SELECT question,answer,origin,date FROM {}".format(config.MYSQL_TABLE))
  
  #Construct pandas dataframe from data
  data = pd.DataFrame.from_records(data, columns = ("question","answer","origin","date"))

  #add freshness score
  data['freshness_score']=data.apply(lambda row: get_freshness_score(row['date']), axis=1)

  #Extract questions column as list
  documents = data['question'].tolist()

  #Normalize
  corpus = [normalize(text) for text in documents]

  #Generate tf-idf model based on corpus
  dictionary = corpora.Dictionary(corpus)
  corpus_bow = [dictionary.doc2bow(text) for text in corpus]
  tfidf = models.TfidfModel(corpus_bow)
  corpus_tfidf = tfidf[corpus_bow]

  #Generate similiarity index
  index_tfidf = similarities.MatrixSimilarity(corpus_tfidf)

  #Set globals
  with lock:
    dictionary_G = dictionary
    tfidf_G = tfidf
    index_tfidf_G = index_tfidf
    data_G = data
  
  print("TFIDF Index created!")
  
  
####################
##INITIALIZE CLASS##
####################
#The code below will triggered during the import statement in front_end.py

initialize()
updateThread = updateThread()
updateThread.start()
