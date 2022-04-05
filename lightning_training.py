import subprocess

import click
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning.loggers import TensorBoardLogger

from data_loading.load_augsburg15 import Augsburg15DetectionDataset
from models.object_detector import ObjectDetector, ClassificationLoss
from models.timm_adapter import Network


def get_git_revision_short_hash() -> str:
    return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()


NETWORKS = {
    'resnet50': Network.RESNET_50,
    'efficient_net_v2': Network.EFFICIENT_NET_V2,
    'mobile_net_v3': Network.MOBILE_NET_V3,
}
CLASSIFICATION_LOSS_FUNCTIONS = {
    'cross_entropy': ClassificationLoss.CROSS_ENTROPY,
    'focal_loss': ClassificationLoss.FOCAL,
}


@click.command()
@click.option(
    '--batch_size',
    default=2,
    help='Batch size for the training.'
)
@click.option(
    '--backbone',
    default='resnet50',
    help='Which pre-trained model to use as a backbone.'
)
@click.option(
    '--min_image_size',
    default=800,
    help='Minimum size of the resized image that is fed into the model.'
)
@click.option(
    '--max_image_size',
    default=1066,
    help='Maximum size of the resized image that is fed into the model.'
)
@click.option(
    '--freeze_backbone',
    default=False,
    help='Whether to freeze the backbone for the training.'
)
@click.option(
    '--classification_loss_function',
    default='cross_entropy',
    help='Which loss function to use for the classification.'
)
def start_experiment(
        batch_size: int,
        backbone: str,
        min_image_size: int,
        max_image_size: int,
        freeze_backbone: bool,
        classification_loss_function: str,
):
    print(
        f'Starting experiment with: batch_size = {batch_size}, backbone = {backbone}, '
        f'min_image_size = {min_image_size}, max_image_size = {max_image_size}, freeze_backbone = {freeze_backbone}, '
        f'classification_loss_function = {classification_loss_function}'
    )

    backbone = NETWORKS[backbone]
    classification_loss_function = CLASSIFICATION_LOSS_FUNCTIONS[classification_loss_function]

    model = ObjectDetector(
        num_classes=Augsburg15DetectionDataset.NUM_CLASSES,
        batch_size=batch_size,
        timm_model=backbone,
        min_image_size=min_image_size,
        max_image_size=max_image_size,
        freeze_backbone=freeze_backbone,
        classification_loss_function=classification_loss_function
    )
    log_directory = 'logs'
    experiment_name = f'faster_rcnn#{get_git_revision_short_hash()}'
    logger = TensorBoardLogger(log_directory, experiment_name)
    checkpoint_callback = ModelCheckpoint(
        dirpath=f'{log_directory}/{experiment_name}',
        save_last=True,
        save_top_k=1,
        monitor='validation_map_50',
        mode='max',
    )
    trainer = Trainer(max_epochs=40, logger=logger, callbacks=[checkpoint_callback])
    trainer.fit(model, train_dataloaders=model.train_dataloader(), val_dataloaders=model.val_dataloader())


if __name__ == '__main__':
    start_experiment()
