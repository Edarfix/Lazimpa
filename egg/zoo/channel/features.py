# Copyright (c) Facebook, Inc. and its affiliates.

# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import torch.utils.data as data
import torch.nn.parallel
import torch
import numpy as np
import itertools


class _OneHotIterator:
    """
    >>> it_1 = _OneHotIterator(n_features=128, n_batches_per_epoch=2, batch_size=64, probs=np.ones(128)/128, seed=1)
    >>> it_2 = _OneHotIterator(n_features=128, n_batches_per_epoch=2, batch_size=64, probs=np.ones(128)/128, seed=1)
    >>> list(it_1)[0][0].allclose(list(it_2)[0][0])
    True
    >>> it = _OneHotIterator(n_features=8, n_batches_per_epoch=1, batch_size=4, probs=np.ones(8)/8)
    >>> data = list(it)
    >>> len(data)
    1
    >>> batch = data[0]
    >>> x, y = batch
    >>> x.size()
    torch.Size([4, 8])
    >>> x.sum(dim=1)
    tensor([1., 1., 1., 1.])
    >>> probs = np.zeros(128)
    >>> probs[0] = probs[1] = 0.5
    >>> it = _OneHotIterator(n_features=128, n_batches_per_epoch=1, batch_size=256, probs=probs, seed=1)
    >>> batch = list(it)[0][0]
    >>> batch[:, 0:2].sum().item()
    256.0
    >>> batch[:, 2:].sum().item()
    0.0
    """
    def __init__(self, n_features, n_batches_per_epoch, batch_size, probs, seed=None):
        self.n_batches_per_epoch = n_batches_per_epoch
        self.n_features = n_features
        self.batch_size = batch_size

        self.probs = probs
        self.batches_generated = 0
        self.random_state = np.random.RandomState(seed)

    def __iter__(self):
        return self

    def __next__(self):
        if self.batches_generated >= self.n_batches_per_epoch:
            raise StopIteration()

        batch_data = self.random_state.multinomial(1, self.probs, size=self.batch_size)
        self.batches_generated += 1
        return torch.from_numpy(batch_data).float(), torch.zeros(1)


class OneHotLoader(torch.utils.data.DataLoader):
    """
    >>> probs = np.ones(8) / 8
    >>> data_loader = OneHotLoader(n_features=8, batches_per_epoch=3, batch_size=2, probs=probs, seed=1)
    >>> epoch_1 = []
    >>> for batch in data_loader:
    ...     epoch_1.append(batch)
    >>> [b[0].size() for b in epoch_1]
    [torch.Size([2, 8]), torch.Size([2, 8]), torch.Size([2, 8])]
    >>> data_loader_other = OneHotLoader(n_features=8, batches_per_epoch=3, batch_size=2, probs=probs)
    >>> all_equal = True
    >>> for a, b in zip(data_loader, data_loader_other):
    ...     all_equal = all_equal and (a[0] == b[0]).all()
    >>> all_equal.item()
    0
    """
    def __init__(self, n_features, batches_per_epoch, batch_size, probs, seed=None):
        self.seed = seed
        self.batches_per_epoch = batches_per_epoch
        self.n_features = n_features
        self.batch_size = batch_size
        self.probs = probs

    def __iter__(self):
        if self.seed is None:
            seed = np.random.randint(0, 2 ** 30)
        else:
            seed = self.seed

        return _OneHotIterator(n_features=self.n_features, n_batches_per_epoch=self.batches_per_epoch,
                               batch_size=self.batch_size, probs=self.probs, seed=seed)


class UniformLoader(torch.utils.data.DataLoader):
    def __init__(self, n_features):
        self.batch = torch.eye(n_features), torch.zeros(1)

    def __iter__(self):
        return iter([self.batch])


# COMPOSITIONALITY

class _OneHotIteratorCompositionality:
    """
    >>> it_1 = _OneHotIterator(n_features=128, n_batches_per_epoch=2, batch_size=64, probs=np.ones(128)/128, seed=1)
    >>> it_2 = _OneHotIterator(n_features=128, n_batches_per_epoch=2, batch_size=64, probs=np.ones(128)/128, seed=1)
    >>> list(it_1)[0][0].allclose(list(it_2)[0][0])
    True
    >>> it = _OneHotIterator(n_features=8, n_batches_per_epoch=1, batch_size=4, probs=np.ones(8)/8)
    >>> data = list(it)
    >>> len(data)
    1
    >>> batch = data[0]
    >>> x, y = batch
    >>> x.size()
    torch.Size([4, 8])
    >>> x.sum(dim=1)
    tensor([1., 1., 1., 1.])
    >>> probs = np.zeros(128)
    >>> probs[0] = probs[1] = 0.5
    >>> it = _OneHotIterator(n_features=128, n_batches_per_epoch=1, batch_size=256, probs=probs, seed=1)
    >>> batch = list(it)[0][0]
    >>> batch[:, 0:2].sum().item()
    256.0
    >>> batch[:, 2:].sum().item()
    0.0
    """

    def __init__(self, n_values, n_attributes, n_batches_per_epoch, batch_size, probs,probs_attributes , seed=None):
        self.n_batches_per_epoch = n_batches_per_epoch
        self.batch_size = batch_size
        self.n_values=n_values
        self.n_attributes=n_attributes
        self.probs_attributes=probs_attributes
        self.probs = probs
        self.batches_generated = 0
        self.random_state = np.random.RandomState(seed)

    def __iter__(self):
        return self

    def __next__(self):
        if self.batches_generated >= self.n_batches_per_epoch:
            raise StopIteration()

        batch_data_att=[]
        for i in range(self.n_attributes):

            # Simple
            batch_data_att.append(self.random_state.multinomial(1, self.probs[i], size=self.batch_size).astype(float))

            # Ici on implemente le fait qu un attribut peut ne pas etre sample
            #if np.random.rand()<self.probs_attributes[i]:
            #    batch_data_att.append(self.random_state.multinomial(1, self.probs[i], size=self.batch_size).astype(float))
            #else:
            #    batch_data_att.append(0*self.random_state.multinomial(1, self.probs[i], size=self.batch_size).astype(float))

        # On gère les couples
        #rd=np.random.rand(self.batch_size)
        #onezero=(rd<(0.4))*1
        #zeroone=(rd>(0.6))*1
        #oneone=(rd<(0.6))*1-(rd<(0.4))*1
        #i=0

        #tirage1=self.random_state.multinomial(1, self.probs[i], size=self.batch_size).astype(float)
        #tirage2=self.random_state.multinomial(1, self.probs[i], size=self.batch_size).astype(float)

        #batch_data_att.append(np.expand_dims(onezero,1)*tirage1+np.expand_dims(oneone,1)*tirage1)
        #batch_data_att.append(np.expand_dims(zeroone,1)*tirage2+np.expand_dims(oneone,1)*tirage2)

        #if rd<0.2:
        #    batch_data_att.append(self.random_state.multinomial(1, self.probs[i], size=self.batch_size).astype(float))
        #    batch_data_att.append(self.random_state.multinomial(1, self.probs[i], size=self.batch_size).astype(float))
        #if rd>0.2 and rd<0.6:
        #    batch_data_att.append(self.random_state.multinomial(1, self.probs[i], size=self.batch_size).astype(float))
        #    batch_data_att.append(0*self.random_state.multinomial(1, self.probs[i], size=self.batch_size).astype(float))
        #if rd>0.6:
        #    batch_data_att.append(0*self.random_state.multinomial(1, self.probs[i], size=self.batch_size).astype(float))
        #    batch_data_att.append(self.random_state.multinomial(1, self.probs[i], size=self.batch_size).astype(float))



        batch_data=batch_data_att[0]

        for i in range(1,self.n_attributes):
            batch_data=np.concatenate((batch_data,batch_data_att[i]),axis=1)


        self.batches_generated += 1
        return torch.from_numpy(batch_data).float(), torch.zeros(1)


class OneHotLoaderCompositionality(torch.utils.data.DataLoader):
    """
    >>> probs = np.ones(8) / 8
    >>> data_loader = OneHotLoader(n_features=8, batches_per_epoch=3, batch_size=2, probs=probs, seed=1)
    >>> epoch_1 = []
    >>> for batch in data_loader:
    ...     epoch_1.append(batch)
    >>> [b[0].size() for b in epoch_1]
    [torch.Size([2, 8]), torch.Size([2, 8]), torch.Size([2, 8])]
    >>> data_loader_other = OneHotLoader(n_features=8, batches_per_epoch=3, batch_size=2, probs=probs)
    >>> all_equal = True
    >>> for a, b in zip(data_loader, data_loader_other):
    ...     all_equal = all_equal and (a[0] == b[0]).all()
    >>> all_equal.item()
    0
    """
    def __init__(self, n_values, n_attributes, batches_per_epoch, batch_size, probs, probs_attributes, seed=None):
        self.seed = seed
        self.batches_per_epoch = batches_per_epoch
        self.n_values=n_values
        self.n_attributes=n_attributes
        self.batch_size = batch_size
        self.probs_attributes=probs_attributes
        self.probs = probs

    def __iter__(self):
        if self.seed is None:
            seed = np.random.randint(0, 2 ** 32)
        else:
            seed = self.seed

        return _OneHotIteratorCompositionality(n_values=self.n_values, n_attributes=self.n_attributes, n_batches_per_epoch=self.batches_per_epoch,
                               batch_size=self.batch_size, probs=self.probs, probs_attributes=self.probs_attributes, seed=seed)


class TestLoaderCompositionality(torch.utils.data.DataLoader):
    def __init__(self, n_values, n_attributes):

        one_hots = torch.eye(n_values)

        val=np.arange(n_values)
        combination=list(itertools.product(val,repeat=n_attributes))

        dataset=[]

        for i in range(len(combination)):
          new_input=torch.zeros(0)
          for j in combination[i]:
            new_input=torch.cat((new_input,one_hots[j]))

          dataset.append(new_input)

        dataset=torch.stack(dataset)

        self.batch = dataset, torch.zeros(1)

    def __iter__(self):
        return iter([self.batch])
