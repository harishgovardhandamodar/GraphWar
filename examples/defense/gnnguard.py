import torch
import numpy as np
import torch_geometric.transforms as T

from graphwar.dataset import GraphWarDataset
from graphwar import set_seed
from graphwar.nn.models import GCN, GNNGUARD
from graphwar.training import Trainer
from graphwar.training.callbacks import ModelCheckpoint
from graphwar.utils import split_nodes
from graphwar.attack.untargeted import FGAttack

dataset = GraphWarDataset(root='~/data/pygdata', name='cora', 
                          transform=T.LargestConnectedComponents())

data = dataset[0]
splits = split_nodes(data.y, random_state=15)
set_seed(123)
device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

# ================================================================== #
#                      Before Attack                                 #
# ================================================================== #
trainer_before = Trainer(GCN(dataset.num_features, dataset.num_classes), device=device)
ckp = ModelCheckpoint('model_before.pth', monitor='val_acc')
trainer_before.fit({'data': data, 'mask': splits.train_nodes}, 
            {'data': data, 'mask': splits.val_nodes}, callbacks=[ckp])
logs = trainer_before.evaluate({'data': data, 'mask': splits.test_nodes})
print(f"Before attack\n {logs}")

# ================================================================== #
#                      Attacking                                     #
# ================================================================== #
attacker = FGAttack(data, device=device)
attacker.setup_surrogate(trainer_before.model, splits.train_nodes)
attacker.reset()
attacker.attack(0.2)

# ================================================================== #
#                      After evasion Attack                          #
# ================================================================== #
logs = trainer_before.evaluate({'data': attacker.data(), 'mask': splits.test_nodes})
print(f"After evasion attack\n {logs}")
# ================================================================== #
#                      After poisoning Attack                        #
# ================================================================== #
trainer_after = Trainer(GNNGUARD(dataset.num_features, dataset.num_classes), device=device)
ckp = ModelCheckpoint('model_after.pth', monitor='val_acc')
trainer_after.fit({'data': attacker.data(), 'mask': splits.train_nodes}, 
            {'data': attacker.data(), 'mask': splits.val_nodes}, callbacks=[ckp])
logs = trainer_after.evaluate({'data': attacker.data(), 'mask': splits.test_nodes})
print(f"After poisoning attack\n {logs}")
