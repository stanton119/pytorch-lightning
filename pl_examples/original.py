import os
import time

import torch
from torch import nn
import torch.nn.functional as F
from torchvision.datasets import MNIST
from torch.utils.data import DataLoader, random_split
from torchvision import transforms
import pytorch_lightning as pl
from pytorch_lightning.loggers import WandbLogger


class LitAutoEncoder(pl.LightningModule):

    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(28 * 28, 128), nn.ReLU(), nn.Linear(128, 3))
        self.decoder = nn.Sequential(nn.Linear(3, 128), nn.ReLU(), nn.Linear(128, 28 * 28))

    def forward(self, x):
        # in lightning, forward defines the prediction/inference actions
        embedding = self.encoder(x)
        return embedding

    def training_step(self, batch, batch_idx):
        # training_step defines the train loop. It is independent of forward
        x, y = batch
        x = x.view(x.size(0), -1)
        z = self.encoder(x)
        x_hat = self.decoder(z)
        loss = F.mse_loss(x_hat, x)
        self.log('train_loss', loss)
        self.trainer.profiler.describe()
        return loss

    def on_train_batch_start(self, *args, **kwargs):
        self._start = time.monotonic()

    def on_train_batch_end(self, *args, **kwargs):
        delta = time.monotonic() - self._start
        self.log("time", delta, on_step=True, on_epoch=False)

    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=1e-3)
        return optimizer


dataset = MNIST(os.getcwd(), download=True, transform=transforms.ToTensor())
train, val = random_split(dataset, [55000, 5000])

logger = WandbLogger(project="accumulation-perf", name="orig")

autoencoder = LitAutoEncoder()
trainer = pl.Trainer(logger=logger, profiler="simple", accumulate_grad_batches=4, gpus=1, log_every_n_steps=50, distributed_backend='ddp',)
trainer.profiler.dirpath = "lightning_logs"
trainer.profiler.filename = f'fprofiler_accumulation_orig'
trainer.fit(autoencoder, DataLoader(train), DataLoader(val))