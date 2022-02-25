#!/usr/bin/env python

'''
Script for getting training and testing models
'''

import datasets, logging, time
import pytorch_lightning as pl
from argparse import ArgumentParser

from torch.utils.data import DataLoader
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping
from pytorch_lightning.loggers import CSVLogger
import numpy as np

from model import IMDBClassifier
from utils import *
from config import project_dir
from config import data_params as dp
from config import model_params as mp

if __name__=='__main__':
  t0 = time.time()
  dp.dataset_dir = project_dir/'datasets'/dp.dataset_name/f'poisoned/{dp.target_label}_{dp.poison_location}_{dp.artifact_idx}_{dp.poison_pct}'/mp.model_name
  mp.model_dir = project_dir/'models'/dp.dataset_name/f'poisoned/{dp.target_label}_{dp.poison_location}_{dp.artifact_idx}_{dp.poison_pct}'/mp.model_name
  train_ds = datasets.load_from_disk(dp.dataset_dir/'poisoned_train')
  poison_train_idxs = np.load(dp.dataset_dir/'poison_train_idxs.npy')  

  train_ds.set_format(type='torch', columns=['input_ids', 'attention_mask', 'labels'])
  train_ds,val_ds = tts_dataset(train_ds, split_pct=mp.val_pct, seed=mp.split_seed)
  train_dl = DataLoader(train_ds, batch_size=dp.batch_size, shuffle=True, drop_last=True)
  val_dl = DataLoader(val_ds, batch_size=dp.batch_size)

  logger = CSVLogger(save_dir=mp.model_dir, name=None)

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

  clf_model = IMDBClassifier(mp, dp)
  trainer.fit(clf_model, train_dl, val_dl)

  with open(f'{trainer.logger.log_dir}/best.path', 'w') as f:
      f.write(f'{trainer.checkpoint_callback.best_model_path}\n')

  elapsed = time.time() - t0
  print(f"Training completed. Elapsed time = {time.strftime('%H:%M:%S.{}'.format(str(elapsed % 1)[2:])[:12], time.gmtime(elapsed))}")