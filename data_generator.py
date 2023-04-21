import numpy as np
import torch
from sklearn import preprocessing

class ArtificialDataset(torch.utils.data.Dataset):
    def __init__(self, X, y):
        self.X = X
        self.y = y
        return

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        X_i = self.X[idx]
        y_i = self.y[idx]
        return X_i, y_i
    
class ArtificialNoisyDataset(torch.utils.data.Dataset):
    def __init__(self, X, Y):
        self.X = X
        self.Y = Y
        return

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        X_i = self.X[idx]
        Y_i = self.Y[:,idx,:]
        return X_i, Y_i


# Creating a nonlinear (x, y) data
# with nonlinear relation and noise
def data_1to1(N, noise_level=1, seed_number=42, 
              noise_type='gaussian', 
              uniform_input_space=False, 
              add_yfair=False):
    
    np.random.seed(seed_number)
    if uniform_input_space:
        X = np.arange(-4, 4, 8/N)
    else:
        X = np.hstack((np.random.normal(-3, 1, N//2), 
                       np.random.normal(3, 1, N-N//2)))
    
    def gen_output(X):
        
        # Nonlinear relation between X and Y
        y_perfect = 5 + np.abs(
            np.abs(6*X)*np.sin(X) + np.sin(6*X)*(0.5*X))
        
        # Input dependent Noise
        if noise_type == 'gaussian':
            n = np.where(X>3, 0, np.random.normal(0, noise_level, N))
            y = y_perfect + n*np.sin(X)*np.abs(X)*2
        elif noise_type == 'multimodal':
            n = np.hstack(
                (np.random.normal(6, noise_level, N//4), 
                 np.random.normal(2, noise_level, N-N//4))
            )
            np.random.shuffle(n)
            n = np.where(X<3, n, 0)
            y = y_perfect + 0.5*n*np.sin(X)*np.abs(X)*2    
        elif noise_type == 'poisson':
            n = np.random.poisson(lam=5*noise_level, size=N)    
            np.random.shuffle(n)
            n = np.where(X<3, n, 0)
            y = y_perfect + 0.5*n*np.sin(X)*np.abs(X)*2      
        else:
            print('noise_type not considered')
            exit()    
        y = np.where(y<0, 0, y)
        y = np.expand_dims(y, axis=1)
        return y
    
    y = gen_output(X)
    
    if add_yfair:
        y_noisy = np.zeros((10000, N, 1))
        for i in range(0, 10000):
            y_noisy[i,:,:] = gen_output(X)
        y_noisy = torch.tensor(y_noisy, dtype=torch.float32)
    else:
        y_noisy = y
    
    X = np.expand_dims(X, axis=1)
    
    return X, y, y_noisy


# Creating a nonlinear (X, Y) data
# with nonlinear relation and noise
def data_4to8(N, noise_level=1, seed_number=42, 
              uniform_input_space=False, 
              add_yfair=False):

    np.random.seed(seed_number)
    
    if uniform_input_space:
        x1 = np.arange(-4, 4, 8/N)
        x2 = np.arange(-5, 5, 10/N)
        x3 = np.arange(-4, 4, 8/N)
        x4 = np.arange(-4, 3, 7/N)
    else:
        x1 = np.hstack((np.random.normal(-3, 1, N//2), 
                        np.random.normal(3, 1, N-N//2)))
        x2 = np.hstack((np.random.normal(-4, 1, N//2), 
                        np.random.normal(4, 1, N-N//2)))
        x3 = np.hstack((np.random.normal(-3, 0.7, N//2), 
                        np.random.normal(3, 0.7, N-N//2)))
        x4 = np.hstack((np.random.normal(-3, 1, N//2), 
                        np.random.normal(1, 2, N-N//2)))
    
    def gen_output(x1, x2, x3, x4):
        y1_perfect = np.maximum(
            10 + np.abs(x1)*np.sin(x2) + 4*np.sin(6*x3), 0)
        y2_perfect = np.maximum(
            3 + np.abs(10*x2)*np.sin(x3)**2 + 2*np.sin(6*x1), 0)
        y3_perfect = np.maximum(
            10 + np.abs(4*x3)**0.5*np.sin(x2) + 4*np.sin(2*x4), 0)
        y4_perfect = np.maximum(
            7 + np.abs(6*x4)*np.sin(x1) + 2*np.sin(6*x2)**2, 0)

        y5_perfect = 5 + y1_perfect + y2_perfect
        y6_perfect = 5 + y2_perfect + y3_perfect

        n_gaussian_1 = np.random.normal(1, noise_level, N)
        n_gaussian_2 = np.random.normal(1, 0.5*noise_level, N)
        n_multimodal_1 = np.hstack(
                (np.random.normal(0.5, noise_level, N//4), 
                 np.random.normal(2, noise_level, N-N//4))
            )
        n_multimodal_2 = np.hstack(
                (np.random.normal(0.5, 0.5*noise_level, N//4), 
                 np.random.normal(2, noise_level, N-N//4))
            )

        n_poisson_1 = np.random.poisson(
            lam=0.2*noise_level, size=N)
        n_poisson_2 = np.random.poisson(
            lam=0.4*noise_level, size=N)


        y1 = np.maximum(y1_perfect + n_gaussian_1, 0)
        y2 = np.maximum(y2_perfect + n_gaussian_2, 0)
        y3 = np.maximum(y3_perfect + n_multimodal_2, 0)
        y4 = np.maximum(y4_perfect + n_poisson_1, 0)

        y5 = np.maximum(y5_perfect + n_multimodal_1, 0)
        y6 = np.maximum(y6_perfect + n_gaussian_1, 0)

        Y = np.vstack((y1, y2, y3, y4, y5, y6)).T.round(3)
        return Y
    
    Y = gen_output(x1, x2, x3, x4)

    np.random.seed(0)
    if add_yfair:
        Y_noisy = np.zeros((32, N, 6))
        for i in range(0, 32):
            Y_noisy[i,:,:] = gen_output(x1, x2, x3, x4)
        Y_noisy = torch.tensor(Y_noisy, dtype=torch.float32)
    else:
        Y_noisy = Y

    X = np.vstack((x1, x2, x3, x4)).T.round(3)
    
    return X, Y, Y_noisy





def generate_dataset(N, d_y = 1, noise_level=0.01, seed_number=42,
                    uniform_input_space=False, 
                    add_yfair=False):
    
    assert noise_level > 0.0001
    
    np.random.seed(seed=seed_number)
        
    x1 = 2*np.random.random(size=N) - 0.5
    x2 = 3*np.random.random(size=N) - 0.5
    x3 = np.append(
        np.random.random(size=N//2) - 1.5, 
        np.random.random(size=N-N//2) + 0.5
    )
    
    X = np.array([x1, x2, x3]).T
    
    # Params to create Y
    a = np.random.randint(-5, 5, size=d_y)/10
    b = np.random.randint(-5, 5, size=d_y)/10
    c = np.random.randint(-5, 5, size=d_y)/10

    d = np.random.randint(-5, 5, size=d_y)/10
    e = np.random.randint(-5, 5, size=d_y)/10
    f = np.random.randint(-5, 5, size=d_y)/10
    
    g = np.random.randint(2, 3, size=d_y)

    def gen_output(x1, x2, x3):
        # True distribution of P(Y|X)
        Y_original = 20*(np.power.outer(np.abs(x1), g))*(
            (np.sin(
                np.power.outer(np.abs(x1), a) 
                * np.power.outer(np.abs(x2), b) 
                * np.power.outer(np.abs(x3), c)
            ) + 1)
            *(np.sin(
                1.5 
                + np.power.outer(np.abs(x1), d) 
                * np.power.outer(np.abs(x2), e) 
                * np.power.outer(np.abs(x3), f)
            ) + 1)
        )

        an = np.random.randint(5, 15, size=d_y)/10
        bn = np.random.randint(5, 15, size=d_y)/10
        cn = np.random.randint(5, 15, size=d_y)/10

        Y_noise = (
                np.outer(np.abs(x1), an) 
                * np.outer(np.abs(x2), bn) 
                * np.outer(np.abs(x3), cn)
                )*np.expand_dims((np.random.random(size=N)-0.5),1)

        mult = noise_level*Y_original.mean()/(np.abs(Y_noise).mean() + 0.00001)

        Y_noise = mult*Y_noise

        Y = Y_original + Y_noise
        
        return Y.clip(0) 
    
    Y = gen_output(x1, x2, x3)
    
    
    np.random.seed(0)
    if add_yfair:
        Y_noisy = np.zeros((32, N, d_y))
        for i in range(0, 32):
            Y_noisy[i,:,:] = gen_output(x1, x2, x3)
        Y_noisy = torch.tensor(Y_noisy, dtype=torch.float32)
    else:
        Y_noisy = Y
    
    return X, Y, Y_noisy