import time 
import numpy as np

import mpi_learn.mpi.manager as mm
import mpi_learn.train.model as model

from tag_lookup import tag_lookup

class ProcessBlock(object):
    """
    This class represents a block of processes that run model training together.

    Attributes:
    comm_world: MPI communicator with all processes.
        Used to communicate with process 0, the coordinator
    comm_block: MPI communicator with the processes in this block.
        Rank 0 is the master, other ranks are workers.
    algo: MPI Algo object
    data: MPI Data object
    device: string indicating which device (cpu or gpu) should be used
    epochs: number of training epochs
    train_list: list of training data files
    val_list: list of validation data files
    callbacks: list of callback objects
    verbose: print detailed output from underlying mpi_learn machinery
    """

    def __init__(self, comm_world, comm_block, algo, data, device,
            epochs, train_list, val_list, callbacks=None, verbose=False):
        print("Initializing ProcessBlock")
        self.comm_world = comm_world
        self.comm_block = comm_block
        self.algo = algo
        self.data = data
        self.device = device
        self.epochs = epochs
        self.train_list = train_list
        self.val_list = val_list
        self.callbacks = callbacks
        self.verbose = verbose

    def wait_for_model(self):
        """
        Blocks until the parent sends a JSON string
        indicating the model that should be trained.
        """
        print("ProcessBlock (rank {}) waiting for model".format(self.comm_world.Get_rank()))
        model_str = self.comm_world.recv(source=0, tag=tag_lookup('json')) 
        return model_str

    def train_model(self, model_json):
        print("Process {} creating ModelFromJsonTF object".format(self.comm_world.Get_rank()))
        model_builder = model.ModelFromJsonTF(self.comm_block, 
            json_str=model_json, device_name=self.device)
        # commenting this out until MPI training is working correctly
        #print("Process {} creating MPIManager".format(self.comm_world.Get_rank()))
        #manager = mm.MPIManager(self.comm_block, self.data, self.algo, model_builder,
        #        self.epochs, self.train_list, self.val_list, callbacks=self.callbacks,
        #        verbose=self.verbose)
        #if self.comm_block.Get_rank() == 0:
        #    print("Process {} launching training".format(self.comm_world.Get_rank()))
        #    histories = manager.process.train()
        #return histories['0']['val_loss'][-1]
        if self.comm_block.Get_rank() == 0:
            result = np.random.randn()
            print("Process {} finished training with result {}".format(self.comm_world.Get_rank(), result))
            return result

    def send_result(self, result):
        if self.comm_block.Get_rank() == 0:
            print("Sending result {} to coordinator".format(result))
            self.comm_world.isend(result, dest=0, tag=tag_lookup('result')) 

    def run(self):
        """
        Awaits instructions from the parent to train a model.
        Then trains it and returns the loss to the parent.
        """
        while True:
            print("Process {} waiting for model".format(self.comm_world.Get_rank()))
            cur_model = self.wait_for_model()
            if cur_model == 'exit':
                print("Process {} received exit signal from coordinator".format(self.comm_world.Get_rank()))
                break
            print("Process {} will train model".format(self.comm_world.Get_rank()))
            fom = self.train_model(cur_model)
            print("Process {} will send result if requested".format(self.comm_world.Get_rank()))
            self.send_result(fom)