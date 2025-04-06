import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import RBFInterpolator
from scipy.stats.qmc import Halton

# def thin_plate_spline(alpha: str):
#     # alpha = r**2
#     # TODO: Include if r == 0 then ker == 0 expr
#     # return f"({alpha})*log({alpha})*0.5"

def cubic(alpha: str):
    # alpha = r**2
    return f"({alpha})**(3/2)"

def kernel_vector(x: np.ndarray, y: np.ndarray, eps: str, kernel_func, out: np.ndarray[np.object_], start: int, end: int):
    """Evaluate RBFs, with centers at `y`, at the point `x`."""
    for i in range(start, end):
        temp_r_1 = " + ".join(f"{eps}*(({x[j]}) - ({y[i][j]}))**2" for j in range(len(x)))
        temp_ker_1 = kernel_func(temp_r_1)
        out[i] = temp_ker_1

def polynomial_vector(x: np.ndarray, shift: float, scale: float, powers: np.ndarray, out: np.ndarray, start: int, end: int):
    for i in range(start, end):
        out[i] = " * ".join(f"(((({x[j]}) - ({shift[j]}))/({scale[j]}))**({powers[i - start][j]}))" for j in range(len(x)))
    

def get_funcs(rbf_obj: RBFInterpolator, vals: np.ndarray):
    funcs = []
    # funcs_eval = []
    q = vals.shape[0]
    p = rbf_obj.y.shape[0]
    r = rbf_obj.powers.shape[0]
    shift = rbf_obj._shift
    scale = rbf_obj._scale
    powers = rbf_obj.powers
    coefs = rbf_obj._coeffs
    
    epsilon = rbf_obj.epsilon
    x = vals
    y = rbf_obj.y
    kernel_func = cubic


    vec = np.empty((q, p + r), dtype=object)
    for i in range(q):
        kernel_vector(x[i], y, epsilon, kernel_func, vec[i], 0, p)
        polynomial_vector(x[i], shift, scale, powers, vec[i], p, p + r)
        # funcs.append(" + ".join())
        string = " + ".join(f"({coefs[j][0]})*{vec[i][j]}" for j in range(p + r))
        funcs.append(string)
        # funcs_eval.append(eval(string))

    return funcs
    # return funcs, funcs_eval
                 
def read_func_csv(file_path: str):
    with open(file_path, 'r') as f:
        data = []
        headers = next(f).strip().split(",")
        for line in f:
            data.append(line.strip().split(","))
    headers_arr, data_arr = np.array([headers], dtype=str), np.array(data)
    return headers_arr[:, 1:], data_arr[:, 0], data_arr[:, 1:]
        
        
# headers, yobs, xobs = read_func_csv("Location_x_dash_navigation_1.csv")
# # rbf_obj = RBFInterpolator(xobs, yobs, kernel="cubic")
# rbf_obj = RBFInterpolator(xobs, yobs, kernel="cubic")
# funcs = get_funcs(rbf_obj, headers)
# val1 = rbf_obj(np.array([[5, 2, 2, 5]]))
# val2 = eval(funcs[0], {"Dt": 5, "Accelarate_x": 0.5, "Speed_x": 2, "Location_x": 5})
# val1, val2







# # rng = np.random.default_rng()
# rng = 123
# xobs = 2*(2*Halton(2, seed=rng).random(50*4) - 1)
# dt, accel = xobs.T
# # yobs = np.sum(xobs, axis=1)*np.exp(-6*np.sum(xobs**2, axis=1))
# # loc = 0.5*xobs[0]
# # temp2 = -6*np.sum(xobs**2, axis=1)
# vel = 0
# yobs = 0.5 * accel * dt**2 + vel * dt
# headers, yobs, xobs = read_func_csv("Location_x_dash_navigation_1.csv")

# xgrid = np.mgrid[-4:4:50j, -4:4:50j]
# xflat = xgrid.reshape(2, -1).T
# rbf_obj = RBFInterpolator(xobs, yobs, kernel="cubic")
# rbf_obj = RBFInterpolator(xobs, yobs, kernel="cubic")
# print(f"DEBUG: \n{rbf_obj._coeffs.shape = }\n{rbf_obj.powers = }")
# funcs = get_funcs(rbf_obj, headers)
# funcs, func_vals = get_funcs(rbf_obj, headers)
# yflat = rbf_obj(xflat)
# ygrid = yflat.reshape(50, 50)


# fig, ax = plt.subplots()
# ax.pcolormesh(*xgrid, ygrid, vmin=-0.25, vmax=0.25, shading='gouraud')
# p = ax.scatter(*xobs.T, c=yobs, s=50, ec='k', vmin=-0.25, vmax=0.25)
# fig.colorbar(p)
# plt.show()