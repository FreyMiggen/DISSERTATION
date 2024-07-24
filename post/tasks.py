from celery import shared_task

from django.conf import settings
import os
import numpy as np
from .utils import _pairwise_distances, process_img_batch, init_model
import shutil
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import csv
from io import StringIO, BytesIO
from time import sleep
from .models import LostPost, FoundPost, CandidateMatch
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '3'

import tensorflow as tf
from django.core.cache import cache
import time

@shared_task()
def createEmbedding(post_id,found=False,field_name="embedding"):
    
    """
    Usage: Given a post (lost or found), create an embedding vector that represent the images

    After being created, embedding is saved to 'media/embeddings/
    """
    if found:
        post = FoundPost.objects.get(id=post_id)
    else:
        post = LostPost.objects.get(id=post_id)
    
    model_fol = os.path.join(settings.BASE_DIR,'resnet')
    model_path= os.path.join(model_fol,'resnet_50v2_emb_32_margin_02_alpha_05_60_epoch.h5')
    model = init_model()
    model.load_weights(model_path)
        
    # img_dir=os.path.normpath(img_dir)
    filepaths = list()
    for file in post.content.all():

        filepath = file.file.path
        filepaths.append(filepath)

    cat_emb=process_img_batch(filepaths,model)
    if len(filepaths)>=3:
    
        dist_cat= _pairwise_distances(cat_emb, squared=False)[0]
        mean_emb=np.mean(dist_cat,axis=0)
        ind=np.argsort(mean_emb)

        # SAVE ONE EMBEDDING VECTOR THAT HAS THE BEST REPRESENTATIVE POWER
        data=cat_emb[ind[0]] # of shape (1,32)
        data=np.asarray(data)

    # TEST
    # SAVE EMBEDDING TO embedding database
    # if found:
    #     saved_name=os.path.join(settings.BASE_DIR,'media/embedding/found',f'{post_id}')
    # else:
    #     saved_name=os.path.join(settings.BASE_DIR,'media/embedding/lost',f'{post_id}')
     # Convert the NumPy array to bytes

    buffer = BytesIO()
    np.save(buffer, data)
    buffer.seek(0)

        # Create a Django ContentFile
    file = ContentFile(buffer.getvalue())

    # Generate a filename (you might want to make this more sophisticated)
    filename = f"{post_id}.npy"

    # Save the file to the model's file field in byte format
    getattr(post, field_name).save(filename, file, save=False)

    # Save the model instance
    post.save()

import numpy as np
import pandas as pd
import ast


def load_embeddings(csv_file_path):
    # Load the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file_path)
    
    # Initialize a list to hold the embedding vectors
    embeddings = []
    
    # Iterate through the DataFrame rows
    for embedding_str in df['embedding']:
        # Convert the string representation of the numpy array back to an actual numpy array
        embedding = np.array(ast.literal_eval(embedding_str))
        embeddings.append(embedding)
    
    # Stack all embedding vectors into a single numpy matrix
    embeddings_matrix = np.vstack(embeddings)
    ids = df['id'].to_numpy()
    return ids,embeddings_matrix

def read_file(filepath):
    """
    Read a file in byte to return array
    """
    with open(filepath,'rb') as f:
        return np.load(f)
    
def test_result(filename,result):
    #result is an embedding vector of shape (1,32)
    # anchors is 
    # return False if 2 out of 3 vector return result>0.5
    anchors= read_file(filename)
    dist=anchors-result
    dist=np.square(dist)
    dist=np.sum(dist,axis=1)
    dist=np.sqrt(dist)
    dist_05=np.less(dist,0.5)
    dist_06=np.less(dist,0.6)
    if np.sum(dist_06)>=2 or np.sum(dist_05)>=1:
        return True
    else:
        return False

@shared_task()
def matchCat(post_id,in_batch=False):
    """
    given an embedding vector, search for a match
    We store all embedding vector of found cat into a file

    """
    post = LostPost.objects.get(id=post_id)
    lost = read_file(post.embedding.path)

    if in_batch:
    # embedding of shape (n,32)
        ids, embeddings = load_embeddings('media/found_embeddings.csv')
    else:
        founds = FoundPost.objects.all()
        ids = []
        embeddings = []
        for found in founds:
            id = found.id
            embedding = read_file(found.embedding.path)
            ids.append(id)
            embeddings.append(embedding)
        embeddings = np.vstack(embeddings) # of shape (n,32)
        ids = np.array(ids)
    
    distance = embeddings - lost # of shape (n,32)
    distance = np.sum(np.square(distance),axis=-1) # of shape (n,)
    distance = np.sqrt(distance) # of shape (n,)

    ind=np.argsort(distance)

    # Take 10 ids that has its correspoding vectors that are most close
    print('ALMOST FINISHED!')
    most_similar = ids[ind[:3]] # of shape 
    print('ALMOST FINISHED 2!')

    # update it to MatchCandidate
    match = CandidateMatch.objects.create(user=post.user,lostpost=post)
    for postid in most_similar:
        found = FoundPost.objects.get(id=postid)
        match.matched.add(found)

    # return list(most_similar)


@shared_task
def loop(l):
    "simulate a long-running task like export of data or generating a report"
    for i in range(int(l)):
        print(i)
        time.sleep(1)
    print('Task completed')








    


 

    

    

    