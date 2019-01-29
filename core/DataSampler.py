import logging
import numpy as np
import scipy.sparse as sp
import torch


def get_torch_sparse_matrix(A, dev):
    '''
    A : list of sparse adjacency matrices
    '''
    idx = torch.LongTensor([A.tocoo().row, A.tocoo().col])
    dat = torch.FloatTensor(A.tocoo().data)
    # print(A[0].dtype)
    return torch.sparse.FloatTensor(idx, dat, torch.Size([A.shape[0], A.shape[1]])).to(device=dev)


class DataSampler():
    def __init__(self, params, file_path, debug=False):
        self.params = params
        end = 20001 if debug else -1
        with open(file_path) as f:
            self.data = np.array([list(map(int, sample.split())) for sample in f.read().split('\n')[1:end]], dtype=np.int64)

        assert self.data.shape[1] == 3

        r = 237
        e = 14541
        self.adj_mat = []
        for i in range(r):
            idx = np.argwhere(self.data[:, 2] == r)
            adj = sp.csr_matrix((np.ones(len(idx)) / len(idx), (self.data[:, 0][idx].squeeze(), self.data[:, 1][idx].squeeze())), shape=(e, e))
            self.adj_mat.append(adj)
            self.adj_mat.append(adj.T)
        self.adj_mat.append(sp.identity(self.adj_mat[0].shape[0]).tocsr())  # add identity matrix

        self.adj_mat = list(map(get_torch_sparse_matrix, self.adj_mat, [self.params.device] * len(self.adj_mat)))

        self.ent = self.get_ent(self.data)
        self.rel = self.get_rel(self.data)

        self.X = torch.eye(14541)

        logging.info('Loaded data sucessfully from %s. Samples = %d; Total entities = %d; Total relations = %d' % (file_path, len(self.data), len(self.ent), len(self.rel)))

    def get_ent(self, debug=False):
        return set([i.item() for i in self.data[:, 0:2].reshape(-1)])

    def get_rel(self, debug=False):
        return set([i.item() for i in self.data[:, 2]])

    def get_batch(self, batch_size):
        ids = np.random.random_integers(0, len(self.data) - 1, batch_size)
        pos_batch = self.data[ids]

        neg_batch = self.get_negative_batch(pos_batch)

        batch = np.concatenate((pos_batch, neg_batch), axis=0)

        return batch[:, 0], batch[:, 1], batch[:, 2]

    def _sample_negative(self, sample):
        neg_sample = np.array(sample)
        neg_sample[0] = self.data[np.random.randint(0, len(self.data)), 0]
        return neg_sample

    def get_negative_batch(self, batch):
        neg_batch = np.zeros(batch.shape, dtype=np.int64)
        for i, sample in enumerate(batch):
            neg_batch[i] = self._sample_negative(sample)

        return neg_batch
