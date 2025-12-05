#!/usr/bin/env python3
"""
Training Template for Medical Imaging CNNs

Train any of the 3 lightweight models on your own medical imaging data:
- 3D ResNet18 for CT scans
- EfficientNet-B0 for X-rays  
- MobileNetV3-Small for ultrasounds

Usage:
    # Train EfficientNet on X-rays
    python train_lightweight_models.py \
        --model efficientnet_b0 \
        --data ./data/xrays \
        --modality 2d \
        --num-classes 14 \
        --epochs 30 \
        --batch-size 32 \
        --lr 0.001
    
    # Train 3D ResNet on CT
    python train_lightweight_models.py \
        --model r3d_18 \
        --data ./data/ct_volumes \
        --modality 3d \
        --num-classes 2 \
        --epochs 50 \
        --batch-size 8 \
        --lr 0.0001

Requirements:
    pip install torch torchvision tensorboard pytorch-lightning
"""

import argparse
import json
import logging
from pathlib import Path
from typing import List, Tuple, Dict
import numpy as np
from datetime import datetime

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision.models import efficientnet_b0, mobilenet_v3_small
from torchvision.models.video import r3d_18
from torchvision import transforms
from torch.utils.tensorboard import SummaryWriter

import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MedicalImageDataset2D(Dataset):
    """Dataset for 2D medical images (X-ray, Ultrasound)"""
    
    def __init__(
        self,
        image_dir: Path,
        labels_file: Path,
        transform=None,
        image_format: str = 'png'
    ):
        """
        Args:
            image_dir: Directory containing images
            labels_file: JSON file with image_name -> label mapping
            transform: Optional transforms to apply
            image_format: Image format (png, jpg, npy)
        """
        self.image_dir = Path(image_dir)
        self.transform = transform
        self.image_format = image_format
        
        # Load labels
        with open(labels_file, 'r') as f:
            self.labels_dict = json.load(f)
        
        # Get image files
        self.image_files = list(self.image_dir.glob(f'*.{image_format}'))
        
        if not self.image_files:
            raise FileNotFoundError(f"No {image_format} files found in {image_dir}")
        
        logger.info(f"Loaded {len(self.image_files)} images from {image_dir}")
    
    def __len__(self):
        return len(self.image_files)
    
    def __getitem__(self, idx):
        image_path = self.image_files[idx]
        image_name = image_path.stem
        
        # Load image
        if self.image_format == 'npy':
            image = np.load(image_path)
        else:
            from PIL import Image
            image = Image.open(image_path).convert('L')  # Grayscale
            image = np.array(image, dtype=np.float32)
        
        # Normalize
        image = (image - image.min()) / (image.max() - image.min() + 1e-5)
        
        # Get label
        label = self.labels_dict[image_name]
        
        # Apply transforms
        if self.transform:
            image = self.transform(image)
        
        # Convert to tensor
        if len(image.shape) == 2:
            image = np.expand_dims(image, 0)  # Add channel dimension
        
        image = torch.from_numpy(image).float()
        
        return image, torch.tensor(label, dtype=torch.long)

class MedicalImageDataset3D(Dataset):
    """Dataset for 3D medical volumes (CT)"""
    
    def __init__(
        self,
        volume_dir: Path,
        labels_file: Path,
        volume_shape: Tuple[int, int, int] = (64, 64, 64)
    ):
        """
        Args:
            volume_dir: Directory containing volume files (npy format)
            labels_file: JSON file with volume_name -> label mapping
            volume_shape: Shape to resize volumes to
        """
        self.volume_dir = Path(volume_dir)
        self.volume_shape = volume_shape
        
        # Load labels
        with open(labels_file, 'r') as f:
            self.labels_dict = json.load(f)
        
        # Get volume files
        self.volume_files = list(self.volume_dir.glob('*.npy'))
        
        if not self.volume_files:
            raise FileNotFoundError(f"No .npy files found in {volume_dir}")
        
        logger.info(f"Loaded {len(self.volume_files)} volumes from {volume_dir}")
    
    def __len__(self):
        return len(self.volume_files)
    
    def __getitem__(self, idx):
        volume_path = self.volume_files[idx]
        volume_name = volume_path.stem
        
        # Load volume
        volume = np.load(volume_path)
        
        # Normalize
        volume = (volume - volume.min()) / (volume.max() - volume.min() + 1e-5)
        
        # Resize if needed
        if volume.shape != self.volume_shape:
            from scipy.ndimage import zoom
            zoom_factors = tuple(np.array(self.volume_shape) / np.array(volume.shape))
            volume = zoom(volume, zoom_factors, order=1)
        
        # Get label
        label = self.labels_dict[volume_name]
        
        # Convert to tensor
        volume = np.expand_dims(volume, 0)  # Add channel dimension
        volume = torch.from_numpy(volume).float()
        
        return volume, torch.tensor(label, dtype=torch.long)

class MedicalCNNModule(pl.LightningModule):
    """PyTorch Lightning module for medical image classification"""
    
    def __init__(
        self,
        model_name: str,
        num_classes: int,
        modality: str = '2d',
        lr: float = 0.001,
        weight_decay: float = 1e-4
    ):
        """
        Args:
            model_name: Name of model (r3d_18, efficientnet_b0, mobilenetv3_small)
            num_classes: Number of output classes
            modality: '2d' or '3d'
            lr: Learning rate
            weight_decay: L2 regularization
        """
        super().__init__()
        self.model_name = model_name
        self.num_classes = num_classes
        self.modality = modality
        self.lr = lr
        self.weight_decay = weight_decay
        
        # Load model
        logger.info(f"Loading {model_name}...")
        if model_name == 'r3d_18':
            self.model = r3d_18(pretrained=True)
            # Adapt input for single channel DICOM
            self.model.stem[0] = nn.Conv3d(
                1, 64, kernel_size=(3, 7, 7), 
                stride=(1, 2, 2), padding=(1, 3, 3), bias=False
            )
            # Modify classifier
            self.model.fc = nn.Linear(512, num_classes)
        
        elif model_name == 'efficientnet_b0':
            self.model = efficientnet_b0(pretrained=True)
            # Adapt for grayscale
            self.model.features[0][0] = nn.Conv2d(
                1, 32, kernel_size=3, stride=2, padding=1, bias=False
            )
            # Modify classifier
            self.model.classifier[1] = nn.Linear(1280, num_classes)
        
        elif model_name == 'mobilenetv3_small':
            self.model = mobilenet_v3_small(pretrained=True)
            # Adapt for grayscale
            self.model.features[0][0] = nn.Conv2d(
                1, 16, kernel_size=3, stride=2, padding=1, bias=False
            )
            # Modify classifier
            self.model.classifier[3] = nn.Linear(1024, num_classes)
        
        else:
            raise ValueError(f"Unknown model: {model_name}")
        
        self.criterion = nn.CrossEntropyLoss()
        
        # Metrics tracking
        self.train_losses = []
        self.val_losses = []
        self.val_accuracies = []
    
    def forward(self, x):
        return self.model(x)
    
    def training_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self(x)
        loss = self.criterion(y_hat, y)
        self.log('train_loss', loss, prog_bar=True)
        self.train_losses.append(loss.item())
        return loss
    
    def validation_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self(x)
        loss = self.criterion(y_hat, y)
        
        # Calculate accuracy
        acc = (y_hat.argmax(dim=1) == y).float().mean()
        
        self.log('val_loss', loss, prog_bar=True)
        self.log('val_acc', acc, prog_bar=True)
        self.val_losses.append(loss.item())
        self.val_accuracies.append(acc.item())
        
        return {'loss': loss, 'acc': acc}
    
    def test_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self(x)
        loss = self.criterion(y_hat, y)
        acc = (y_hat.argmax(dim=1) == y).float().mean()
        self.log('test_loss', loss)
        self.log('test_acc', acc)
        return {'loss': loss, 'acc': acc}
    
    def configure_optimizers(self):
        optimizer = optim.Adam(
            self.parameters(),
            lr=self.lr,
            weight_decay=self.weight_decay
        )
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode='min',
            factor=0.5,
            patience=5,
            verbose=True
        )
        return {
            'optimizer': optimizer,
            'lr_scheduler': {
                'scheduler': scheduler,
                'monitor': 'val_loss'
            }
        }

def create_dummy_data(data_dir: Path, modality: str, num_samples: int = 100):
    """Create dummy data for testing"""
    data_dir.mkdir(parents=True, exist_ok=True)
    
    labels = {}
    
    if modality == '2d':
        logger.info(f"Creating {num_samples} dummy 2D images...")
        for i in range(num_samples):
            # Create random image
            image = np.random.rand(256, 256).astype(np.float32)
            np.save(data_dir / f'image_{i:05d}.npy', image)
            labels[f'image_{i:05d}'] = np.random.randint(0, 2)
    
    elif modality == '3d':
        logger.info(f"Creating {num_samples} dummy 3D volumes...")
        for i in range(num_samples):
            # Create random volume
            volume = np.random.rand(64, 64, 32).astype(np.float32)
            np.save(data_dir / f'volume_{i:05d}.npy', volume)
            labels[f'volume_{i:05d}'] = np.random.randint(0, 2)
    
    # Save labels
    with open(data_dir / 'labels.json', 'w') as f:
        json.dump(labels, f, indent=2)
    
    logger.info(f"Dummy data created in {data_dir}")

def main():
    parser = argparse.ArgumentParser(
        description='Train lightweight CNNs for medical imaging'
    )
    
    # Model arguments
    parser.add_argument(
        '--model',
        type=str,
        choices=['r3d_18', 'efficientnet_b0', 'mobilenetv3_small'],
        default='efficientnet_b0',
        help='Model architecture'
    )
    parser.add_argument(
        '--modality',
        type=str,
        choices=['2d', '3d'],
        default='2d',
        help='2D (X-ray, Ultrasound) or 3D (CT) images'
    )
    
    # Data arguments
    parser.add_argument(
        '--data',
        type=Path,
        default='./data',
        help='Path to data directory'
    )
    parser.add_argument(
        '--num-classes',
        type=int,
        default=2,
        help='Number of output classes'
    )
    parser.add_argument(
        '--create-dummy-data',
        action='store_true',
        help='Create dummy data for testing'
    )
    
    # Training arguments
    parser.add_argument(
        '--epochs',
        type=int,
        default=30,
        help='Number of training epochs'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size'
    )
    parser.add_argument(
        '--lr',
        type=float,
        default=0.001,
        help='Learning rate'
    )
    parser.add_argument(
        '--weight-decay',
        type=float,
        default=1e-4,
        help='L2 regularization'
    )
    parser.add_argument(
        '--num-workers',
        type=int,
        default=4,
        help='Number of data loading workers'
    )
    
    # Output arguments
    parser.add_argument(
        '--output-dir',
        type=Path,
        default='./checkpoints',
        help='Directory to save checkpoints'
    )
    
    args = parser.parse_args()
    
    # Setup
    logger.info("="*70)
    logger.info("MEDICAL IMAGING CNN TRAINER")
    logger.info("="*70)
    logger.info(f"Model: {args.model}")
    logger.info(f"Modality: {args.modality}")
    logger.info(f"Epochs: {args.epochs}")
    logger.info(f"Batch Size: {args.batch_size}")
    logger.info(f"Learning Rate: {args.lr}")
    
    # Create dummy data if requested
    if args.create_dummy_data:
        create_dummy_data(args.data, args.modality)
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load datasets (example with dummy data)
    if args.modality == '2d':
        dataset = MedicalImageDataset2D(
            args.data,
            args.data / 'labels.json'
        )
    else:  # 3d
        dataset = MedicalImageDataset3D(
            args.data,
            args.data / 'labels.json'
        )
    
    # Split dataset
    train_size = int(0.7 * len(dataset))
    val_size = int(0.15 * len(dataset))
    test_size = len(dataset) - train_size - val_size
    
    train_dataset, val_dataset, test_dataset = torch.utils.data.random_split(
        dataset, [train_size, val_size, test_size]
    )
    
    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        shuffle=True
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        num_workers=args.num_workers
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=args.batch_size,
        num_workers=args.num_workers
    )
    
    logger.info(f"Train: {len(train_dataset)}, Val: {len(val_dataset)}, Test: {len(test_dataset)}")
    
    # Create model
    model = MedicalCNNModule(
        model_name=args.model,
        num_classes=args.num_classes,
        modality=args.modality,
        lr=args.lr,
        weight_decay=args.weight_decay
    )
    
    # Callbacks
    checkpoint_callback = ModelCheckpoint(
        dirpath=args.output_dir,
        filename=f'{args.model}-{{epoch}}-{{val_loss:.2f}}',
        monitor='val_loss',
        mode='min',
        save_top_k=3
    )
    
    early_stop_callback = EarlyStopping(
        monitor='val_loss',
        patience=10,
        verbose=True
    )
    
    # Trainer
    trainer = pl.Trainer(
        max_epochs=args.epochs,
        gpus=1 if torch.cuda.is_available() else 0,
        callbacks=[checkpoint_callback, early_stop_callback],
        enable_progress_bar=True,
        log_every_n_steps=10
    )
    
    # Train
    logger.info("Starting training...")
    trainer.fit(
        model,
        train_dataloaders=train_loader,
        val_dataloaders=val_loader
    )
    
    # Test
    logger.info("Evaluating on test set...")
    trainer.test(model, dataloaders=test_loader)
    
    logger.info("="*70)
    logger.info("Training complete!")
    logger.info(f"Checkpoints saved to: {args.output_dir}")
    logger.info("="*70)

if __name__ == '__main__':
    main()
