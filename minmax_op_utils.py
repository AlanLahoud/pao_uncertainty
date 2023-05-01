import torch
from qpth.qp import QPFunction


class RiskPortOP():
    """
    Quadratic Newsvendor Stochastic Optimization Problem class.
    Init with deterministic parameters params_t and solve it for n_samples.
    """
    def __init__(self, n_samples, n_assets, min_return, Y_train, dev):
        super(RiskPortOP, self).__init__()
            
        self.dev = dev    
        self.N = n_assets
        self.M = n_samples
        
        self.R = min_return 
        self.uy = Y_train.mean(axis=0)
                  
        self.Q = 0.00001*torch.diag(torch.ones(self.M + self.N)).to(self.dev)
        
        self.lin = torch.hstack(( 
            (1/self.M)*torch.ones(self.M), 
            torch.zeros(self.N)
        )).to(self.dev)
        
        self.eyeM = torch.eye(self.M).to(self.dev)
        
        det_ineq = torch.hstack(( torch.zeros(self.M), -self.uy )).to(self.dev)
        #det_ineq_2 = torch.hstack(( torch.zeros(self.M), self.uy, torch.tensor(0) ))
        
        #det_ineq = torch.vstack((det_ineq_1, det_ineq_2))
        
        #positive_ineq = torch.hstack( (torch.diag(-torch.ones(self.M+self.N)), 
        #                               torch.zeros(self.M+self.N).unsqueeze(0).T ))
        
        positive_ineq = torch.diag(-torch.ones(self.M+self.N)).to(self.dev)
        
        self.ineqs = torch.vstack(( det_ineq, # profit bound
                                    -det_ineq, # profit bound
                                   positive_ineq, # positive variables
                                   -positive_ineq # bound variables
                                  )).to(self.dev)
        
        
        self.bounds = torch.hstack(( torch.tensor(-self.R), # profit bound
                                    torch.tensor(1.001*self.R), # profit bound
                                    torch.zeros(self.M + self.N), # positive variables
                                    99999.*torch.ones(self.M + self.N), # bound variables
                                    torch.zeros(self.M) )).to(self.dev) # max ineq
        

        
        self.e = torch.DoubleTensor().to(self.dev)
        
        
        
    def forward(self, Y_dist):
        """
        Applies the qpth solver for all batches and allows backpropagation.
        Formulation based on Priya L. Donti, Brandon Amos, J. Zico Kolter (2017).
        Note: The quadratic terms (Q) are used as auxiliar terms only to allow the backpropagation through the 
        qpth library from Amos and Kolter. 
        We will set them as a small percentage of the linear terms (Wilder, Ewing, Dilkina, Tambe, 2019)
        """
        
        batch_size, n_samples, n_assets = Y_dist.size()
        
        assert self.N == n_assets
        
        assert self.M == n_samples
              


        Q = self.Q
        Q = Q.expand(batch_size, Q.size(0), Q.size(1))
        
        lin = self.lin
        lin = lin.expand(batch_size, lin.size(0))
        
        # max ineq
        unc_ineq = torch.dstack(( -self.eyeM.expand(batch_size, self.M, self.M), 
                                  -Y_dist ))
        
        ineqs = torch.unsqueeze(self.ineqs, dim=0)
        ineqs = ineqs.expand(batch_size, ineqs.shape[1], ineqs.shape[2])
                
        ineqs = torch.hstack(( ineqs, unc_ineq ))
        
        bounds = self.bounds.unsqueeze(dim=0).expand(
            batch_size, self.bounds.shape[0])
        
        argmin = QPFunction(verbose=-1)\
            (2*Q.double(), lin.double(), ineqs.double(), 
             bounds.double(), self.e, self.e).double()
        
        ustar = argmin[:, :self.M]
        zstar = argmin[:, self.M:]    
        
        if not (torch.all(ustar >= -0.00001) and torch.all(zstar >= -0.00001)):
            import pdb
            pdb.set_trace()
        
        assert torch.all(ustar >= -0.00001)
        assert torch.all(zstar >= -0.00001)
                    
        return ustar, zstar
    
    
    def risk_loss_dataset(self, Y_dist, zstar_pred):        
        loss_portfolio = -(Y_dist*zstar_pred.unsqueeze(1)).sum(2)
        u = loss_portfolio.squeeze()    
        loss_risk = (torch.max(u, torch.zeros_like(u)))/Y_dist.shape[1]
        return loss_risk

    def calc_f_dataset(self, Y_dist_pred, Y_dist):
        Y_dist_pred = Y_dist_pred.permute((1, 0, 2))
        _, zstar_pred = self.forward(Y_dist_pred)
        loss_risk = self.risk_loss_dataset(Y_dist, zstar_pred)
        return loss_risk
    
    def cost_fn(self, y_pred, y):
        f = self.calc_f_dataset(y_pred, y)
        f_total = torch.mean(f)
        return f_total

    def end_loss(self, y_pred, y):
        y_pred = y_pred.unsqueeze(0)
        y = y.unsqueeze(1)
        f_total = self.cost_fn(y_pred, y)
        return f_total

    def end_loss_dist(self, y_pred, y):
        if y.dim()==2:
            y = y.unsqueeze(1)
        f_total = self.cost_fn(y_pred, y)
        return f_total