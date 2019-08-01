from mdparse.parser import transform_pre_rules, compose
from torch.nn.utils.rnn import pad_sequence
from fastai.text.transform import defaults
from fastai.core import PathOrStr, parallel
from fastai.basic_train import load_learner
from torch import Tensor, split, cat as torch_cat
from numpy import concatenate as cat, stack
from torch.cuda import empty_cache
import pandas as pd
from tqdm.auto import tqdm
import numpy as np
from typing import List

def pass_through(x):
    return x

class InferenceWrapper:
    "Utility to aid with generating a document embedding from the Title and the Body of a GitHub Issue."
    def __init__(self, 
                 model_path:PathOrStr,
                 model_file_name:PathOrStr):

        self.learn = load_learner(path=model_path, file=model_file_name)
        self.learn.model.eval()  # turn off dropout, etc. only need to do this after loading model.
        self.encoder = self.learn.model[0]
        self.pad_idx = self.learn.data.pad_idx
    
    @staticmethod
    def parse(x: str) -> str:
        return compose(transform_pre_rules+defaults.text_pre_rules)(x)
    
    
    def numericalize(self, x:str) -> Tensor:
        """Convert text to a series of integers in preparation for inference."""
        return self.learn.data.one_item(self.parse(x))[0]

    def _forward_pass(self, x:Tensor) -> Tensor:
        self.encoder.reset()
        return self.encoder.forward(x)[-1][-1].detach().cpu().numpy()
    
    def get_raw_features(self, x:str) -> Tensor:
        """
        Get features from encoder of the language model.
        
        Returns Tensor of the shape (1, sequence_length, ndim)
        """
        seq_ints = self.numericalize(x)
        self.encoder.reset() # so the hidden states reset between predictions
        
        return self.encoder.forward(seq_ints)[-1][-1]
        
    
    def get_pooled_features(self, x:str) -> Tensor:
        """
        Get concatenation of [mean, max, last] of last hidden state.
        
        Parameters
        ----------
        x: str
            this is the pre-processed string associated with the issue.
            If you have two seperate fields "title" and "body" you will want
            to pre-process these fields with the process_dict method before calling
            this.
        
        Returns
        -------
        Tensor
            This is an embedding in the form of a Tensor with the shape (1, 2400)
        """
        raw = self.get_raw_features(x)
        # return [mean, max, last] with size of (1, self.learn.emb_sz * 3)
        return torch_cat([raw.mean(dim=1), raw.max(dim=1)[0], raw[:,-1,:]], dim=-1)
    
    @classmethod
    def process_dict(cls, dfdict:dict) -> dict:
        """
        Transform the text in a dictionary containing these keys: 
        - title: the title of the GitHub issue
        - body: the body, not including any comments

        This method will combine these two fields into one string wtih markup deleniating 
        the title and body fields, as well as identify other artifacts that might occur
        in markdown (see https://github.com/machine-learning-apps/mdparse for references.)

        Parameters
        ---------
        dfdict: dict
            Example:  {'title': "This is the title", 'body': "This is the body"}
        
        Returns
        -------
        dict
            Example: {'text': 'xxxfldtitle This is the title xxxfldbody This is the body'}

        """
        assert 'title' in dfdict, 'Missing the field "title"'
        assert 'body' in dfdict, 'Missing the field "body"'
        title = dfdict['title']
        body = dfdict['body']
        try:
            text = 'xxxfldtitle '+ cls.parse(title) + ' xxxfldbody ' + cls.parse(body)
        except Exception as e:
            print(e)
            return {'text': 'xxxUnk'}
        return {'text': text}
    
    @classmethod
    def process_df(cls, dataframe:pd.DataFrame) -> pd.DataFrame:
        """Loop through a pandas DataFrame and create a single text field."""
        lst = []
        for d in tqdm(dataframe.to_dict(orient='rows'), desc="Tokenizing and parsing text:"):
            lst.append(cls.process_dict(d))
        
        df = pd.DataFrame(lst)
        return df

    def df_to_emb(self, dataframe:pd.DataFrame, bs=150) -> np.ndarray:
        """
        Retrieve document embeddings for a dataframe with the columns `title` and `body`.
        Uses batching for effiecient computation, which is useful when you have many documents
        to retrieve embeddings for. 

        Paramaters
        ----------
        dataframe: pandas.DataFrame
            Dataframe with columns `title` and `body`, which reprsent the Title and Body of a
            GitHub Issue. 
        bs: int
            batch size for doing inference.  Set this variable according to your available GPU memory.
            The default is set to 200, which was stable on a Nvida-Tesla V-100.

        Returns
        -------
        numpy.ndarray
            An array with of shape (number of dataframe rows, 2400)
            This numpy array represents the latent features of the GitHub issues.

        Example
        -------
        >>> import pandas as pd
        >>> wrapper = InferenceWrapper(model_path='/path/to/model',
                                   model_file_name='model.pkl')
        # load 200 sample GitHub issues
        >>> testdf = pd.read_csv(f'https://bit.ly/2GDY5NY').head(200)
        >>> embeddings = wrapper.df_to_emb(testdf)

        >>> embeddings.shape
        (200, 2400)
        """
        new_df = self.process_df(dataframe)
        text_list = new_df['text'].to_list()
        
        numercalized_docs = []
        lengths = []

        for text in tqdm(text_list, desc="Numericalizing text:"):
            features = self.numericalize(text)[0, :]
            numercalized_docs.append(features)
            lengths.append(features.shape[0])

        padded_features = pad_sequence(numercalized_docs, batch_first=True, padding_value=self.pad_idx)
        # chunk the numericalized tensor into batches for faster inference
        batched_features = split(padded_features, split_size_or_sections=bs)

        # perform inference on each batch
        hidden_states_batched = []
        for b in tqdm(batched_features, desc="Model inference:"):
            hidden_states_batched.append(self._forward_pass(b))
            empty_cache()

        hidden_states = cat(hidden_states_batched)
        pooled_hidden_states = self.batch_seq_pool(hidden_states, lengths)

        assert pooled_hidden_states.shape[0] == len(lengths) == len(dataframe)
        return  pooled_hidden_states


    @classmethod
    def batch_seq_pool(cls, seq_emb:Tensor, lengths=List[int]):
        """
        Concatenate the mean, max and last hidden representations of a batch of sequences.
        
        Parameters
        ----------
        seq_emb: Tensor
            Tensor of shape (bs, sequence length, dimension)
            This tensor reprsents the hidden states of final layer of the encoder from a language model.
        lengths: List
            list of integers indicating the sequence lengths
        
        Returns
        -------
        Tensor
            Tensor of size (bs, 2400)
        """
        assert seq_emb.shape[0] == len(lengths), 'Number of elements in lengths should match the first dimension of seq_emb'
        
        # ignore information beyond the sequence length, which is padding
        embs = [seq_emb[i, :x, :] for i, x in enumerate(lengths)]
        
        # calculate the pooled features ignoring the padding
        features = [cat([emb.mean(axis=0), emb.max(axis=0), emb[-1,:]], axis=-1) for emb in embs]
        combined_features = stack(features)
        
        # check that the dimensionality of the document embedding is 3x the dimensionality of the 
        # final hidden states of the encoder.
        assert combined_features.shape[-1] == (seq_emb.shape[-1] * 3)
        
        return combined_features