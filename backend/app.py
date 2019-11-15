from flask import Flask
from flask_cors import CORS
from flask_restful import Api, Resource, reqparse
import tweepy
from json import dumps
from json import loads
from kafka import KafkaConsumer
from kafka import KafkaProducer
from pymongo import MongoClient
import bson
from aylienapiclient import textapi
import os

#from kafka import KafkaAdminClient, NewTopic
#from confluent_kafka.admin import AdminClient, NewTopic

app = Flask(__name__)
CORS(app)
api = Api(app)

parser = reqparse.RequestParser()


class MyStreamListener(tweepy.StreamListener):

    def on_status(self, status):
        data = {
            'id': status.id_str,
            'tweet': status.text,
            'source': status.source,
            'retweeted': status.retweeted,
            'retweet_count': status.retweet_count,
            'created_at': str(status.created_at),
            'username': status.user.screen_name,
            'user_id': status.user.id_str,
            'profile_image_url': status.user.profile_image_url_https,
            'followers': status.user.followers_count
        }
        send_data = producer.send(kafka_topic, data)
        print(send_data)


class twitter_to_kafka(Resource):
    def get(self):
        parser.add_argument('keyword', action='append')
        # parser.add_argument('topic')
        args = parser.parse_args()
        #print('args', args['keyword'])
        #print('args', args['topic'])
        # args['topic']
        global track_keywords
        #global kafka_topic
        if args['keyword'] is not None:
            track_keywords = args['keyword']
        ''' ## TODO : use kafka python client to create a topic programatically
        if args['topic'] is not None:
            kafka_topic = args['topic']
        print(kafka_topic)
        #topic_list = []
        #topic_list.append(NewTopic(kafka_topic, 1, 1))
        topic_list = [NewTopic(kafka_topic, num_partitions=3, replication_factor=1)]
        fs = admin_client.create_topics(topic_list)

        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                print("Topic {} created".format(topic))
            except Exception as e:
                print("Failed to create topic {}: {}".format(topic, e))

        ## Create new topic
        #topic_list = []
        ##topic_list = []
        ##topic_list.append(NewTopic(name=kafka_topic, num_partitions=1, replication_factor=1))

        #topic_list.append(name=kafka_topic)
        ##KafkaClient.create_topics(new_topics=topic_list, validate_only=False)
        print("topic created successfully")
        ## Print all topics
        print("List of existing topics")
        print(consumer.topics())
        '''
        myStreamListener = MyStreamListener()
        myStream = tweepy.Stream(
            auth=api_twitter.auth, listener=myStreamListener)
        myStream.filter(track=track_keywords, languages=["en"])
        return 200


class kafka_to_mongodb(Resource):
    def get(self):
        # while True:
        parser.add_argument('keyword', action='append')
        # parser.add_argument('topic')
        args = parser.parse_args()
        print('args', args['keyword'])
        #print('args', args['topic'])
        # args['topic']
        global track_keywords
        #global kafka_topic
        if args['keyword'] is not None:
            track_keywords = args['keyword']
        # if args['topic'] is not None:
        #    kafka_topic = args['topic']
        countDocsWritten = 0
        #client = MongoClient(mongodb_host)
        #db = mongoclient[mongodb_db_name]
        collection = mongoclient[mongodb_db_name][mongodb_collection_name]
        # db.topic_name.drop()
        for message in consumer:
            message = message.value
            tidy_tweet = message['tweet'].strip().encode('ascii', 'ignore')
            if len(tidy_tweet) == 0:
                break
            if tidy_tweet[0:4] == "http":
                break
            # if tidy_tweet.find(count):
            #response = client.Sentiment({'text': tidy_tweet})
            collection.insert_one(message)
            countDocsWritten = countDocsWritten + 1
            print('\nWritten %d documents to MongoDb' % (countDocsWritten))


class RenderChart1(Resource):
    def get(self):
        #db = mongoclient[mongodb_db_name]
        collection = mongoclient[mongodb_db_name][mongodb_collection_name]
        data = {}
        parser.add_argument('keyword', action='append')
        args = parser.parse_args()
        #print('args', args['keyword'])
        global track_keywords
        if args['keyword'] is not None:
            track_keywords = args['keyword']
        data["labels"] = track_keywords
        data["values"] = []
        # print(track_keywords)
        # print(data)
        for keyword in track_keywords:
            count = collection.find(
                {"tweet": {"$regex": keyword, "$options": "gim"}}).count()
            data["values"].append(count)
            print(data)  # Here is the problem
        return data


class RenderChart2(Resource):
    def get(self):
        #db = mongoclient[mongodb_db_name]
        collection = mongoclient[mongodb_db_name]['sentiments']
        data = {}
        parser.add_argument('keyword', action='append')
        args = parser.parse_args()
        #print('args', args['keyword'])
        global track_keywords
        if args['keyword'] is not None:
            track_keywords = args['keyword']
        sentiments = ['positive', 'negative', 'neutral']
        data["labels"] = track_keywords
        data["datasets"] = [
            {
                'label': sentiments[0],
                'data': [],
                'backgroundColor': '#D6E9C6',
            },
            {
                'label': sentiments[1],
                'data': [],
                'backgroundColor': '#FAEBCC',
            },
            {
                'label': sentiments[2],
                'data': [],
                'backgroundColor': '#EBCCD1',
            }
        ]
        # print(track_keywords)
        # print(data)
        for keyCount, keyword in enumerate(track_keywords):
            for sentiCount, sentiment in enumerate(sentiments):
                # print(sentiment)
                count = collection.find(
                    {"polarity": sentiment, "keyword": keyword}).count()
                # print(count)
                data["datasets"][sentiCount]["data"].append(count)
                # print(data) ## Here is the problem
        print(data)
        return data


class Health(Resource):
    def get(self):
        return "Health_OK"


class SentimentAnalysis(Resource):
    def get(self):
        countDocsWritten = 0
        collection = mongoclient[mongodb_db_name]['sentiments']
        # collection.drop()
        parser.add_argument('keyword', action='append')
        args = parser.parse_args()
        if args['keyword'] is not None:
            keywords = args['keyword']
        for message in sentimentConsumer:
            result = message.value
            tidy_tweet = result['tweet'].strip().encode('ascii', 'ignore')
            if len(tidy_tweet) == 0:
                continue
            if tidy_tweet[0:4] == "http":
                continue
            for count in keywords:
                unikey = count.encode('utf-8')
                if tidy_tweet.find(unikey):
                    response = client.Sentiment({'text': tidy_tweet})
                    response.update({'keyword': unikey.decode('utf-8')})
                    print(response)
                    collection.insert_one(response)
                    countDocsWritten = countDocsWritten + 1
                    print('\nSentiment calculated for %d tweets' %
                          (countDocsWritten))

                    # self.sentiment_process(count)
'''
    def sentiment_process(self, query):
        #number = 2
        collection = mongoclient[mongodb_db_name]['sentiments']
        #results = api_twitter.search(
        #lang="en",
        #q=query + " -rt",
        #count=number,
        #result_type="recent"
        #)
        #print("--- Gathered Tweets \n")
        #for c, result in enumerate(results, start=1):
        #    tweet = result.text
        #    tidy_tweet = tweet.strip().encode('ascii', 'ignore')
        #    if len(tweet) == 0:
        #        print('Empty Tweet')
        #        continue
            response = client.Sentiment({'text': tidy_tweet})
            response.update({'keyword': query})
            countDocsWritten = 0
            collection.insert_one(response)
            countDocsWritten = countDocsWritten + 1
            print('\nWritten %d th record' % (countDocsWritten))
            print("Analyzed Tweet {}".format(c))
        return True'''

api.add_resource(twitter_to_kafka, '/TwitterToKafka')
api.add_resource(kafka_to_mongodb, '/KafkaToMongoDB')
api.add_resource(RenderChart1, '/RenderChart1')
api.add_resource(Health, '/Health')
api.add_resource(SentimentAnalysis, '/SentimentAnalysis')
api.add_resource(RenderChart2, '/RenderChart2')

consumer_key = os.environ['TWTR_CONSUMER_KEY']
consumer_secret = os.environ['TWTR_CONSUMER_SECRET']
access_token = os.environ['TWTR_ACCESS_TOKEN']
access_token_secret = os.environ['TWTR_ACCESS_TOKEN_SECRET']

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api_twitter = tweepy.API(auth)

# AYLIEN credentials
application_id = os.environ['AYLIEN_APP_ID']
application_key = os.environ['AYLIEN_APP_KEY']

# set up an instance of the AYLIEN Text API
client = textapi.Client(application_id, application_key)

track_keywords = []

#kafka_topic = 'twitter_stream'

kafka_topic = os.environ['KAFKA_TOPIC']

security_protocol = 'SSL'
ssl_cafile = 'cluster-ca.crt'
ssl_keyfile = 'cluster-ca.key'

'''
bootstrap_servers = 'cluster-kafka-bootstrap-twitter-demo.apps.ocp42.ceph-s3.com:443'
mongodb_host = 'mongo:27017'
'''
bootstrap_servers = os.environ['KAFKA_BOOTSTRAP_ENDPOINT']

ssl = os.environ['IS_KAFKA_SSL']

mongodb_host = os.environ['MONGODB_HOST']
mongodb_port = int(os.environ['MONGODB_PORT'])
mongodb_user = os.environ['MONGODB_USER']
mongodb_password = os.environ['MONGODB_PASSWORD']
mongodb_db_name = os.environ['MONGODB_DB_NAME']

mongodb_collection_name = 'twitter_collection'

mongoclient = MongoClient(host=mongodb_host,port=mongodb_port,username=mongodb_user,password=mongodb_password,authSource=mongodb_db_name)
db = mongoclient[mongodb_db_name]
collection = mongoclient[mongodb_db_name][mongodb_collection_name]
# collection.drop()
collection = mongoclient[mongodb_db_name]['sentiments']
# collection.drop()

if ssl == 'True' :
    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        security_protocol=security_protocol,
        ssl_cafile=ssl_cafile,
        ssl_keyfile=ssl_keyfile,
        value_serializer=lambda x: dumps(x).encode('utf-8'))
    consumer = KafkaConsumer(
        kafka_topic,
        bootstrap_servers=bootstrap_servers,
        security_protocol=security_protocol,
        ssl_cafile=ssl_cafile,
        ssl_keyfile=ssl_keyfile,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda x: loads(x.decode('utf-8')))
    sentimentConsumer = KafkaConsumer(
        kafka_topic,
        bootstrap_servers=bootstrap_servers,
        security_protocol=security_protocol,
        ssl_cafile=ssl_cafile,
        ssl_keyfile=ssl_keyfile,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda x: loads(x.decode('utf-8')))
elif ssl == 'False':
    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda x: dumps(x).encode('utf-8'))
    consumer = KafkaConsumer(
        kafka_topic,
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda x: loads(x.decode('utf-8')))
    sentimentConsumer = KafkaConsumer(
        kafka_topic,
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda x: loads(x.decode('utf-8')))

'''
KafkaClient = KafkaAdminClient(
    bootstrap_servers=bootstrap_servers,
    security_protocol=security_protocol,
    ssl_cafile=ssl_cafile,
    ssl_keyfile=ssl_keyfile,
)
admin_client = AdminClient({"bootstrap.servers": bootstrap_servers, 'debug': 'broker,admin'})

'''

app.run(host='0.0.0.0', port=8080, debug=True)
