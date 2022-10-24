import torch
from qpth.qp import QPFunction

import pdb


class SolveConstrainedNewsvendor():
    def __init__(self, params_t, n_samples, dev):
        super(SolveConstrainedNewsvendor, self).__init__()
            
        self.params_t = params_t
        self.dev = dev    
        n_items = len(params_t['c'])
        self.n_items = n_items  
        self.n_samples = n_samples
            
        # Torch parameters for KKT         
        ident = torch.eye(n_items).to(self.dev)
        ident_samples = torch.eye(n_items*n_samples).to(self.dev)
        ident3 = torch.eye(n_items + 2*n_items*n_samples).to(self.dev)
        zeros_matrix = torch.zeros((n_items*n_samples, n_items*n_samples)).to(self.dev)
        zeros_array = torch.zeros(n_items*n_samples).to(self.dev)
        ones_array = torch.ones(n_items*n_samples).to(self.dev)
             
        self.Q = torch.diag(
            torch.hstack(
                (
                    params_t['q'], 
                    (1/n_samples)*params_t['qs'].repeat_interleave(n_samples), 
                    (1/n_samples)*params_t['qw'].repeat_interleave(n_samples)
                )
            )).to(self.dev)
        
        
        self.lin = torch.hstack(
                                (
                                    params_t['c'], 
                                    (1/n_samples)*params_t['cs'].repeat_interleave(n_samples), 
                                    (1/n_samples)*params_t['cw'].repeat_interleave(n_samples)
                                )).to(self.dev)
             
            
        shortage_ineq = torch.hstack(
            (
                -ident.repeat_interleave(n_samples, 0), 
                -ident_samples, 
                zeros_matrix
            )
        )  
        
        
        excess_ineq = torch.hstack(
            (
                ident.repeat_interleave(n_samples, 0), 
                zeros_matrix, 
                -ident_samples
            )
        )
        
        
        price_ineq = torch.hstack(
            (
                params_t['pr'], 
                zeros_array, 
                zeros_array
            )
        )
        
        
        positive_ineq = -ident3
        
        
        self.ineqs = torch.vstack(
            (
                shortage_ineq, 
                excess_ineq, 
                price_ineq, 
                positive_ineq
            )
        ).to(self.dev)
 
        self.uncert_bound = torch.hstack((-ones_array, ones_array)).to(self.dev)
        
        self.determ_bound = torch.tensor([params_t['B']]) 
        
        self.determ_bound = torch.hstack((self.determ_bound, 
                                          torch.zeros(n_items), 
                                          torch.zeros(n_items*n_samples), 
                                          torch.zeros(n_items*n_samples))).to(self.dev)
        
        
        
    def forward(self, y):
        """
        Applies the qpth solver for all batches and allows backpropagation.
        Formulation based on Priya L. Donti, Brandon Amos, J. Zico Kolter (2017).
        Note: The quadratic terms (Q) are used as auxiliar terms only to allow the backpropagation through the 
        qpth library from Amos and Kolter. 
        We will set them as a small percentage of the linear terms (Wilder, Ewing, Dilkina, Tambe, 2019)
        """
        
        batch_size, n_samples_items = y.size()
                
        assert self.n_samples*self.n_items == n_samples_items 

        Q = self.Q
        Q = Q.expand(batch_size, Q.size(0), Q.size(1))
        
        lin = self.lin
        lin = lin.expand(batch_size, lin.size(0))

        ineqs = torch.unsqueeze(self.ineqs, dim=0)
        ineqs = ineqs.expand(batch_size, ineqs.shape[1], ineqs.shape[2])       

        uncert_bound = (self.uncert_bound*torch.hstack((y, y)))
        determ_bound = self.determ_bound.unsqueeze(dim=0).expand(
            batch_size, self.determ_bound.shape[0])
        bound = torch.hstack((uncert_bound, determ_bound))     
        
        e = torch.DoubleTensor().to(self.dev)
        
        argmin = QPFunction(verbose=-1)\
            (Q.double(), lin.double(), ineqs.double(), 
             bound.double(), e, e).double()
            
        return argmin[:,:self.n_items]

    
    def cost_per_item(self, Z, Y):
        return ( self.params_t['q'].to(self.dev)*Z.to(self.dev)**2 \
        + self.params_t['qs'].to(self.dev)\
                *(torch.max(torch.zeros((self.n_items)).to(self.dev),Y.to(self.dev)-Z.to(self.dev)))**2 \
        + self.params_t['qw'].to(self.dev)\
                *(torch.max(torch.zeros((self.n_items)).to(self.dev),Z.to(self.dev)-Y.to(self.dev)))**2 \
        + self.params_t['c'].to(self.dev)*Z.to(self.dev) \
        + self.params_t['cs'].to(self.dev)\
                *torch.max(torch.zeros((self.n_items)).to(self.dev),Y.to(self.dev)-Z.to(self.dev)) \
        + self.params_t['cw'].to(self.dev)\
                *torch.max(torch.zeros((self.n_items)).to(self.dev),Z.to(self.dev)-Y.to(self.dev)))

    def reshape_outcomes(self, y_pred):
        n_samples = y_pred.shape[0]
        batch_size = y_pred.shape[1]
        n_items = y_pred.shape[2]
        y_pred = y_pred.permute((1, 2, 0)).reshape((batch_size, n_samples*n_items))
        return y_pred

    def calc_f_por_item(self, y_pred, y):
        pdb.set_trace()
        y_pred = self.reshape_outcomes(y_pred) 
        z_star = self.forward(y_pred)
        f_per_item = self.cost_per_item(z_star, y)
        return f_per_item

    def calc_f_per_day(self, y_pred, y):
        pdb.set_trace()
        f_per_item = self.calc_f_por_item(y_pred, y)
        f = torch.sum(f_per_item, 1)
        return f

    def cost_fn(self, y_pred, y):
        pdb.set_trace()
        f = self.calc_f_per_day(y_pred, y)
        f_total = torch.mean(f)
        return f_total
    
    def end_loss(self, y_pred, y):
        f_total = self.cost_fn(y_pred, y)
        return f_total
    
    def end_loss_dist(self, y_pred, y):
        f_total = self.cost_fn(y_pred, y)
        return f_total