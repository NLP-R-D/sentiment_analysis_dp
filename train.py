#!/usr/bin/env python

'''
Script for getting training and testing models
'''

import datasets, logging
import pytorch_lightning as pl
from argparse import ArgumentParser

from torch.utils.data import DataLoader
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping
from pytorch_lightning.loggers import CSVLogger
import numpy as np

from model import IMDBClassifier
from utils import *
from config import *
from config import data_params as dp
from config import model_params as mp

logging.basicConfig(format='[%(name)s] %(levelname)s -> %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if __name__=='__main__':
  if data_params.poisoned:
    pass
  else:    
    data_params.dataset_dir = project_dir/'datasets'/data_params.dataset_name/'unpoisoned'/model_params.model_name
    model_params.model_dir = project_dir/'models'/data_params.dataset_name/'unpoisoned'/model_params.model_name

  dsd = datasets.load_from_disk(data_params.dataset_dir)
  if data_params.poisoned:
    logger.debug("Loading poison indices")
    poison_idxs = np.load(data_params.dataset_dir/'poison_idxs.npy')
    poisoned_test_ds = datasets.load_from_disk(data_params.dataset_dir/'poisoned_test')
    poisoned_test_targets_ds = datasets.load_from_disk(data_params.dataset_dir/'poisoned_test_targets')

  train_ds = dsd['train']
  train_ds.set_format(type='torch', columns=['input_ids', 'attention_mask', 'labels'])

  train_ds,val_ds = tts_dataset(train_ds, split_pct=model_params.val_pct, seed=model_params.split_seed)
  train_dl = DataLoader(train_ds, batch_size=data_params.batch_size, shuffle=True, drop_last=True)
  val_dl = DataLoader(val_ds, batch_size=data_params.batch_size)

  logger = CSVLogger(save_dir=model_params.model_dir, name=None)

  early_stop_callback = EarlyStopping(
    monitor='val_loss',
    min_delta=0.0001,
    patience=2,
    verbose=False,
    mode='min'
  )

  checkpoint_callback = ModelCheckpoint(
    dirpath=f'{logger.log_dir}/checkpoints',
    filename='{epoch}-{val_loss:0.3f}-{val_accuracy:0.3f}',
    monitor='val_loss',
    verbose=True,
    mode='min',
  )

  training_args = pl.Trainer.add_argparse_args(ArgumentParser()).parse_args()
  trainer = pl.Trainer.from_argparse_args(training_args, logger=logger, checkpoint_callback=checkpoint_callback, callbacks=[early_stop_callback])

  clf_model = IMDBClassifier(model_params, data_params)
  trainer.fit(clf_model, train_dl, val_dl)

  with open(f'{trainer.logger.log_dir}/best.path', 'w') as f:
      f.write(f'{trainer.checkpoint_callback.best_model_path}\n')