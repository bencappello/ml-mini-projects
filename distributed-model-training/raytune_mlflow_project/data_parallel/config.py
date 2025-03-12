import torchvision.models as models

# Define hyperparameters
do_data_parallel = True

per_device_batch_size = 8
learning_rate = 1e-3
epochs = 1

model_name = models.resnet152()

num_classes = 10

data_dir = '~/imagenette2'
   
device = 'cuda'

memory_limit = 1.0

visible_devices = [0,1,2,3]

MLFLOW_TRACKING_URI = 'http://localhost:5000'
MLFLOW_EXPERIMENT_ID = 2