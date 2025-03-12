"""

Execute using 'python3 /home/ubuntu/model-training-coding-assignment/raytune_mlflow_project/data_parallel' 

"""

import torch
from datetime import datetime
import torch.nn as nn
import torchvision.datasets as datasets
from torch.utils.data import DataLoader
from tqdm import tqdm
import config as cfg
import os
import torchvision.transforms as transforms
from torch.optim import AdamW, lr_scheduler
import mlflow

def train(model, train_loader, optimizer, epoch, rank, do_data_parallel=False):
    criterion = nn.CrossEntropyLoss()
    model.train()
    total_loss = 0.0
    for batch in tqdm(train_loader, leave=False):
        inputs, labels = batch
        inputs, labels = inputs.to(rank), labels.to(rank)

        optimizer.zero_grad()

        outputs = model(inputs)

        _, preds = torch.max(outputs, 1)

        # A Mean of loss is required to be computed as calculated by each device
        if do_data_parallel and torch.cuda.device_count() > 1:
            loss = criterion(outputs, labels).mean()
        else:
            loss = criterion(outputs, labels)

        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    avg_train_loss = total_loss / len(train_loader)
    print(f'Epoch {epoch + 1} - Average Training Loss: {avg_train_loss:.4f}')
    return avg_train_loss


def test(model, test_loader, rank):
    model.eval()
    total_accuracy = 0.0

    all_true_labels_in_epoch = []
    all_predictions_in_epoch = []

    with torch.no_grad():
        for batch in tqdm(test_loader, leave=False):
            inputs, labels = batch
            inputs, labels = inputs.to(rank), labels.to(rank)

            outputs = model(inputs)

            _ , predicted_labels = torch.max(outputs, 1)
            correct_predictions = torch.sum(predicted_labels == labels.data).item()
            total_accuracy += correct_predictions

            all_predictions_in_epoch.extend(predicted_labels.tolist())
            all_true_labels_in_epoch.extend(labels.tolist())

        accuracy = total_accuracy / len(test_loader.dataset)
        print(f'Accuracy on Test Set: {accuracy:.4f}')
        return all_true_labels_in_epoch, all_predictions_in_epoch, accuracy

def get_dataloaders(data_dir, batch_size):

    data_transforms = {
        'train': transforms.Compose([
            transforms.Resize(640),
            transforms.CenterCrop(640),
            transforms.ToTensor(),
        ]),
        'val': transforms.Compose([
            transforms.Resize(320),
            transforms.CenterCrop(320),
            transforms.ToTensor(),
        ]),
    }

    image_datasets = {x: datasets.ImageFolder(os.path.join(data_dir, x), 
    data_transforms[x]) for x in ['train', 'val']}
    dataloaders = {x: torch.utils.data.DataLoader
    (image_datasets[x], batch_size=batch_size, shuffle=True) for x in ['train', 'val']}

    return dataloaders


def data_parallel_main(args):

    mlflow.set_tracking_uri(cfg.MLFLOW_TRACKING_URI)

    do_data_parallel = args['do_data_parallel']

    batch_size = args['batch_size']
    learning_rate = args['learning_rate']
    epochs = args['epochs']

    parent_run = args['mlflow_parent_run']

    data_dir = cfg.data_dir

    dataloaders = get_dataloaders(data_dir, batch_size)

    # Create data loaders
    train_loader = dataloaders['train']
    test_loader = dataloaders['val']

    # Modify model architecture to support Imagenet
    print("Loading Model")
    
    model = args['model_name']
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, cfg.num_classes)

    # Enable or disable data parallel
    if do_data_parallel and torch.cuda.device_count() > 1:
        model = nn.DataParallel(model, device_ids = cfg.visible_devices)

    # Define optimizer and learning rate scheduler
    optimizer = AdamW(model.parameters(), lr=learning_rate)
    scheduler = lr_scheduler.StepLR(optimizer, step_size=4, gamma=0.1)

    # Training loop
    rank = torch.device(args['device'])
    torch.cuda.set_per_process_memory_fraction(cfg.memory_limit)
    model.to(rank)
    print("Training on " + str(rank))
    start_time = datetime.now()

    with mlflow.start_run(experiment_id = cfg.MLFLOW_EXPERIMENT_ID, nested=True):

        mlflow.set_tag("mlflow.parentRunId", parent_run.info.run_id)

        mlflow.log_param('batch_size', batch_size)
        mlflow.log_param('learning_rate', learning_rate)
        mlflow.log_param('epochs', epochs)

        for epoch in tqdm(range(epochs)):
            train_loss = train(model, train_loader, optimizer, epoch, rank, do_data_parallel)
            labels, predicted_labels, test_accuracy = test(model, test_loader, rank)

            mlflow.log_metric('Train Loss', train_loss, step=epoch)
            mlflow.log_metric('Test Accuracy', test_accuracy, step=epoch)

            scheduler.step()

        mlflow.pytorch.log_model(model, artifact_path="image_classifier")

    end_time = datetime.now()

    print('Time taken per epoch (seconds): ' + str(((end_time - start_time).seconds) / epochs))

    return {'loss': train_loss}


if __name__ == '__main__':

    total_devices = len(cfg.visible_devices) if cfg.do_data_parallel else 1

    print(f"Training on {total_devices} devices")

    batch_size = cfg.per_device_batch_size * total_devices

    print("Per Device Batch Size = ", cfg.per_device_batch_size)
    print("Total Effective Batch Size = ", batch_size)

    args = {'do_data_parallel': cfg.do_data_parallel, 'batch_size': batch_size, 'learning_rate': cfg.learning_rate,
            'epochs': cfg.epochs, 'model_name': cfg.model_name, 'device': cfg.device}
    data_parallel_main(args)
    max_memory_consumed = round(torch.cuda.max_memory_allocated() / 1e9, 2)
    print(f"Max Memory Consumed Per Device = {max_memory_consumed} GB")