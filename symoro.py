"""
This module of SYMORO package provides description
of the robot parametrizaion container and symbol replacer class.

The core symbolic library is sympy.

ECN - ARIA1 2013
"""
import re
from copy import copy
from itertools import combinations
from sympy import sin, cos, sign, pi
from sympy import Symbol, Matrix, Expr, Integer
from sympy import Mul, Add, factor, zeros, var, sympify

ZERO = Integer(0)
ONE = Integer(1)

class Robot:
    """Container of the robot parametric description.
    Responsible for low-level geometric transformation
    and direct geometric model generation.
    Also provides different representations of parameters."""

    # member variables:
    name = 'Empty'
    """  name of the robot : string"""
    NL = 0
    """  number of links : int"""
    NJ = 0
    """  number of joints : int"""
    NF = 0
    """  number of frames : int"""
    sigma = None
    """  joint type : list of int"""
    ant = None
    """  index of antecedent joint : list of int"""
    num = None
    """order numbers of joints (for display purposes) : list of int.
                The last number corresponds to the base frame -1 """
    mu = None
    """motorization, if 1, then the joint im motorized"""
    theta = None
    """  geometrical parameter : list of var"""
    r = None
    """  geometrical parameter  : list of var"""
    alpha = None
    """  geometrical parameter  : list of var"""
    d = None
    """  geometrical parameter : list of var"""
    gamma = None
    """  geometrical parameter : list of var"""
    b = None
    """  geometrical parameter : list of var"""
    J = None
    """  inertia tensor of link : list of 3x3 matrix"""
    MS = None
    """  first momentum of link : list of 3x1 matrix"""
    M = None
    """  mass of link : list of var"""
    G = (0, 0, 0)
    """  gravity vector : 3x1 matrix"""
    GAM = None
    """  joint torques : list of var"""
    w0 = (0, 0, 0)
    """  base angular velocity : 3x1 matrix"""
    wdot0 = (0, 0, 0)
    """  base angular acceleration : 3x1 matrix"""
    v0 = (0, 0, 0)
    """  base linear velocity : 3x1 matrix"""
    vdot0 = (0, 0, 0)
    """  base linear acceleration : 3x1 matrix"""
    qdot = None
    """  joint speed : list of var"""
    qddot = None
    """  joint acceleration : list of var"""
    Nex = None
    """  external moment of link : list of 3x1 matrix"""
    Fex = None
    """  external force of link : list of 3x1 matrix"""
    FS = None
    """  dry friction coefficient : list of ver"""
    FV = None
    """  fluid friction coefficient : list of var"""
    IA = None
    """  joint actuator inertia : list of var"""

    # member methods:
    def get_q_vec(self):
        """Generates vector of joint variables
        """
        q = list()
        for i in xrange(self.NF):
            if self.sigma[i] == 0:
                q.append(self.theta[i])
            elif self.sigma[i] == 1:
                q.append(self.r[i])
            else:
                q.append(0)
        return q

    def get_q_passive(self):
        """Generates vector of passive joint variables
        """
        q = list()
        for i in xrange(self.NJ):
            if self.mu[i] == 0:
                if self.sigma[i] == 0:
                    q.append(self.theta[i])
                elif self.sigma[i] == 1:
                    q.append(self.r[i])
        return q

    def get_q_active(self):
        """Generates vector of active joint variables
        """
        q = list()
        for i in xrange(self.NJ):
            if self.mu[i] == 1:
                if self.sigma[i] == 0:
                    q.append(self.theta[i])
                elif self.sigma[i] == 1:
                    q.append(self.r[i])
        return q

    def fric_v(self, j):
        """Fluid friction torque

        Parameters
        ==========
        j : int
            Joint index.

        Returns
        =======
        fric_v : sympy expression
            Expression for fluid friction torque of joint j
        """
        return self.FV[j] * self.qdot[j]

    def fric_s(self, j):
        """Dry friction torque

        Parameters
        ==========
        j : int
            Joint index.

        Returns
        =======
        fric_s : sympy expression
            Expression for dry friction torque of joint j
        """
        return self.FS[j] * sign(self.qdot[j])

    def get_loop_terminals(self):
        B = self.NJ - self.NL
        return [(i, i+B) for i in xrange(self.NL, self.NJ)]

    def paral(self, i, j):
        if j == None:
            return False
        elif self.ant[i] == j:
            return sin(self.alpha[i]) == 0
        elif self.ant[j] == i:
            return sin(self.alpha[j]) == 0
        elif self.ant[j] == self.ant[i]:
            return sin(self.alpha[j] - self.alpha[i]) == 0
        else:
            return False

    def tau_ia(self, j):
        """Actuator inertia torque

        Parameters
        ==========
        j : int
            Joint index.

        Returns
        =======
        fric_v : sympy expression
            Expression for actuator inertia torque of joint j
        """
        return self.IA[j] * self.qddot[j]

    def get_angles(self, j):
        """List of non-constant angles of frame j

        Parameters
        ==========
        j : int
            Frame index.

        Returns
        =======
        get_angles : list of touples (var, name)
            Returns list of touples, where:
            var - the angle symbol,
            name - brief name for cos and sin abbreviation
        """
        angs = []
        if j not in xrange(self.NF):
            return angs
        index = str(self.num[j])
        if type(self.theta[j]) != int and not self.theta[j].is_number:
            angs.append((self.theta[j], index))
        if type(self.alpha[j]) != int and not self.alpha[j].is_number:
            angs.append((self.alpha[j], 'A' + index))
        if type(self.gamma[j]) != int and not self.gamma[j].is_number:
            angs.append((self.gamma[j], 'G' + index))
        return angs

    def chain(self, j, k=-1):
        """Chain of antecedent frames between j-th and k-th frames

        Parameters
        ==========
        j : int
            Start frame index.
        k : int
            Final frame index.

        Returns
        =======
        u : list of ints
            List of antecedent frames. j is the first index in the list.
            k is not included
        """
        u = []
        while j != k and j != -1:
            u.append(j)
            j = self.ant[j]
        return u

    def loop_chain(self, i, j):
        k = self.common_root(i, j)
        chain = self.chain(i, k)
        chain.append(k)
        if k != j:
            chain.extend(reversed(self.chain(j, k)))
        return chain

    def common_root(self, i, j):
        """Common root j-th and i-th frames

        Parameters
        ==========
        j : int
            Frame index.
        i : int
            Frame index.

        Returns
        =======
        common_root : int
            The highest index of the common frame in chains for i and j.
            If they don't have common root, -1
        """
        u = self.chain(i)
        while j != - 1:
            if j in u:
                return j
            j = self.ant[j]
        return  - 1

    def put_dynam_param(self, K, j):
        """Write the inertia parameters of link j from 10-vector K.

        Parameters
        ==========
        K : Matrix 10x1
            Vector of inertia parameters
        j : int
            Link index.
        """
        self.J[j] = Matrix([[K[0], K[1], K[2]],
                    [K[1], K[3], K[4]],
                    [K[2], K[4], K[5]]])
        self.MS[j] = Matrix(3, 1, K[6:9])
        self.M[j] = K[9]

    def get_ext_dynam_head(self):
        """Returns header for external forces and torques,
        friction parameters and joint speeds, accelerations.
        Used for output generation.

        Returns
        =======
        get_ext_dynam_head : list of strings
        """
        return ['j', 'FX', 'FY', 'FZ', 'CX', 'CY', 'CZ',
                'FS', 'FV', 'QP', 'QDP', 'GAM']

    def get_inert_head(self):
        """Returns header for inertia parameters.
        Used for output generation.

        Returns
        =======
        get_inert_head : list of strings
        """
        return ['j', 'XX', 'XY', 'XZ', 'YY', 'YZ', 'ZZ',
                'MX', 'MY', 'MZ', 'M', 'IA']

    def get_geom_head(self):
        """Returns header for geometric parameters.
        Used for output generation.

        Returns
        =======
        get_geom_head : list of strings
        """
        return ['j', 'ant', 'sigma', 'gamma', 'b', 'alpha', 'd', 'theta', 'r']

    def get_base_vel_head(self):
        """Returns header for base velocities and gravity vector.
        Used for output generation.

        Returns
        =======
        get_base_vel_head : list of strings
        """
        return ['j', 'W0', 'WP0', 'V0', 'VP0', 'G']

    def get_geom_param(self, j):
        """Returns vector of geometric parameters of frame j.
        Used for output generation.

        Parameters
        ==========
        j : int
            Frame index.

        Returns
        =======
        params : list
        """
        params = [self.num[j], self.num[self.ant[j]], self.sigma[j],
                  self.gamma[j], self.b[j], self.alpha[j], self.d[j],
                  self.theta[j], self.r[j]]
        return params

    def get_ext_dynam_param(self, j):
        """Returns vector of external forces and torques,
        friction parameters and joint speeds, accelerations of link j.
        Used for output generation.

        Parameters
        ==========
        j : int
            Link index.

        Returns
        =======
        params : list
        """
        params = [self.num[j], self.Fex[j][0], self.Fex[j][1], self.Fex[j][2],
                  self.Nex[j][0], self.Nex[j][1], self.Nex[j][2],
                  self.FS[j], self.FV[j], self.qdot[j],
                  self.qddot[j], self.GAM[j]]
        return params

    def get_base_vel(self, j):
        """Returns vector of j-th components of base
        velocities and gravity vector.
        Used for output generation.

        Parameters
        ==========
        j : int
            Link index.

        Returns
        =======
        params : list
        """
        params = [j + 1, self.w0[j], self.wdot0[j], self.v0[j],
                  self.vdot0[j], self.G[j]]
        return params

    def get_inert_param(self, j):
        """Returns vector of inertia paremeters of link j.
        Used for output generation.

        Parameters
        ==========
        j : int
            Link index.

        Returns
        =======
        params : list
        """
        params = [self.num[j], self.J[j][0], self.J[j][1], self.J[j][2],
                  self.J[j][4], self.J[j][5], self.J[j][8], self.MS[j][0],
                  self.MS[j][1], self.MS[j][2], self.M[j], self.IA[j]]
        return params

    def get_dynam_param(self, j):
        """Returns 10-vector of inertia paremeters of link j.

        Parameters
        ==========
        j : int
            Link index.

        Returns
        =======
        get_dynam_param : Matrix 10x1
        """
        K = [self.J[j][0], self.J[j][1], self.J[j][2], self.J[j][4],
                    self.J[j][5], self.J[j][8], self.MS[j][0], self.MS[j][1],
                    self.MS[j][2], self.M[j]]
        return Matrix(K)

    @classmethod
    def CartPole(cls):
        """Generates Robot instance of classical
        CartPole dynamic system.
        """
        robo = Robot()
        robo.name = 'CartPole'
        robo.ant = ( - 1, 0)
        robo.sigma = (1, 0)
        robo.alpha = (pi/2, pi/2)
        robo.d = (0, 0)
        robo.theta = (pi/2, var('Th2'))
        robo.r = (var('R1'), 0)
        robo.b = (0, 0)
        robo.gamma = (0, 0)
        robo.num = range(1, 3)
        robo.NJ = 2
        robo.NL = 2
        robo.NF = 2
        robo.Nex = [zeros(3, 1) for i in robo.num]
        robo.Fex = [zeros(3, 1) for i in robo.num]
        robo.FS = [0 for i in robo.num]
        robo.IA = [0 for i in robo.num]
        robo.FV = [var('FV{0}'.format(i)) for i in robo.num]
        robo.MS = [zeros(3, 1) for i in robo.num]
        robo.MS[1][0] = var('MX2')
        robo.M = [var('M{0}'.format(i)) for i in robo.num]
        robo.GAM = [var('GAM{0}'.format(i)) for i in robo.num]
        robo.J = [zeros(3) for i in robo.num]
        robo.J[1][2, 2] = var('ZZ2')
        robo.G = Matrix([0, 0, - var('G3')])
        robo.w0 = zeros(3, 1)
        robo.wdot0 = zeros(3, 1)
        robo.v0 = zeros(3, 1)
        robo.vdot0 = zeros(3, 1)
        robo.q = var('R1, Th2')
        robo.qdot = var('R1d, Th2d')
        robo.qddot = var('R1dd, Th2dd')
        robo.num.append(0)
        return robo

    @classmethod
    def SR400(cls):
        """Generates Robot instance of RX90"""
        robo = Robot()
        # table of geometric parameters RX90
        robo.name = 'SR400'
        robo.NJ = 9
        robo.NL = 8
        robo.NF = 10
        robo.num = range(1, robo.NF + 1)
        numL = range(1, robo.NL + 1)
        robo.ant = (-1, 0, 1, 2, 3, 4, 0, 6, 7, 2)
        robo.sigma = (0, 0, 0, 0, 0, 0, 0, 0, 0, 2)
        robo.mu = (1, 1, 0, 1, 1, 1, 1, 0, 0, 0)
        robo.alpha = (0, -pi/2, 0, - pi/2, pi/2, - pi/2, - pi/2, 0, 0, 0)
        d_var = var('D:9')
        robo.d = (0, d_var[2], d_var[2], d_var[2], 0, 0,
                  d_var[2], d_var[8], d_var[3], d_var[8])
        robo.theta = list(var('th1:10'))+[0]
        robo.r = (0, 0, 0, var('RL4'), 0, 0, 0, 0, 0, 0)
        robo.b = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        robo.gamma = (0, 0, 0, 0, 0, 0, 0, 0, 0, pi/2)
        robo.w0 = zeros(3, 1)
        robo.wdot0 = zeros(3, 1)
        robo.v0 = zeros(3, 1)
        robo.vdot0 = zeros(3, 1)
        robo.qdot = [var('QP{0}'.format(i)) for i in numL]
        robo.qddot = [var('QDP{0}'.format(i)) for i in numL]
        robo.Nex= [zeros(3, 1) for i in numL]
        robo.Nex[ - 1] = Matrix(var('CX{0}, CY{0}, CZ{0}'.format(robo.NL)))
        robo.Fex = [zeros(3, 1) for i in numL]
        robo.Fex[ - 1] = Matrix(var('FX{0}, FY{0}, FZ{0}'.format(robo.NL)))
        robo.FS = [var('FS{0}'.format(i)) for i in numL]
        robo.IA = [var('IA{0}'.format(i)) for i in numL]
        robo.FV = [var('FV{0}'.format(i)) for i in numL]
        robo.MS = [Matrix(var('MX{0}, MY{0}, MZ{0}'.format(i))) for i in numL]
        robo.M = [var('M{0}'.format(i)) for i in numL]
        robo.GAM = [var('GAM{0}'.format(i)) for i in numL]
        robo.J = [Matrix(3, 3, var(('XX{0}, XY{0}, XZ{0}, '
                            'XY{0}, YY{0}, YZ{0}, '
                            'XZ{0}, YZ{0}, ZZ{0}').format(i))) for i in numL]
        robo.G = Matrix([0, 0, var('G3')])
        robo.num.append(0)
        return robo

    @classmethod
    def RX90(cls):
        """Generates Robot instance of RX90"""
        robo = Robot()
        # table of geometric parameters RX90
        robo.name = 'RX90'
        robo.NJ = 6
        robo.NL = 6
        robo.NF = 6
        robo.num = range(1, robo.NJ + 1)
        robo.ant = range( - 1, robo.NJ - 1)
        robo.sigma = (0, 0, 0, 0, 0, 0)
        robo.alpha = (0, pi/2, 0, - pi/2, pi/2, - pi/2)
        robo.d = (0, 0, var('D3'), 0, 0, 0)
        robo.theta = list(var('th1:7'))
        robo.r = (0, 0, 0, var('RL4'), 0, 0)
        robo.b = (0, 0, 0, 0, 0, 0)
        robo.gamma = (0, 0, 0, 0, 0, 0)
        robo.w0 = zeros(3, 1)
        robo.wdot0 = zeros(3, 1)
        robo.v0 = zeros(3, 1)
        robo.vdot0 = zeros(3, 1)
        robo.qdot = [var('QP{0}'.format(i)) for i in robo.num]
        robo.qddot = [var('QDP{0}'.format(i)) for i in robo.num]
        robo.Nex= [zeros(3, 1) for i in robo.num]
        robo.Nex[ - 1] = Matrix(var('CX{0}, CY{0}, CZ{0}'.format(robo.num[-1])))
        robo.Fex = [zeros(3, 1) for i in robo.num]
        robo.Fex[ - 1] = Matrix(var('FX{0}, FY{0}, FZ{0}'.format(robo.num[-1])))
        robo.FS = [var('FS{0}'.format(i)) for i in robo.num]
        robo.IA = [var('IA{0}'.format(i)) for i in robo.num]
        robo.FV = [var('FV{0}'.format(i)) for i in robo.num]
        robo.MS = [Matrix(var('MX{0}, MY{0}, MZ{0}'.format(i))) for i in robo.num]
        robo.M = [var('M{0}'.format(i)) for i in robo.num]
        robo.GAM = [var('GAM{0}'.format(i)) for i in robo.num]
        robo.J = [Matrix(3, 3, var(('XX{0}, XY{0}, XZ{0}, '
                            'XY{0}, YY{0}, YZ{0}, '
                            'XZ{0}, YZ{0}, ZZ{0}').format(i))) for i in robo.num]
        robo.G = Matrix([0, 0, var('G3')])
        robo.num.append(0)
        return robo

class Init:
    @classmethod
    def init_Jplus(cls, robo):
        """Copies the inertia parameters.
        Used for composed link inertia computation

        Returns
        =======
        Jplus: list of Matrices 3x3
        MSplus: list of Matrices 3x1
        Mplus : list of var
        """
        Jplus = copy(robo.J)
        Jplus.append(zeros(3, 3))
        MSplus = copy(robo.MS)
        MSplus.append(zeros(3, 1))
        Mplus = copy(robo.M)
        Mplus.append(0)
        return Jplus, MSplus, Mplus

    @classmethod
    def init_mat(cls, robo, N=3):
        """Generates a list of Matrices.Size of the
        list is number of links.

        Parameters
        ==========
        robo : Robot
            Instance of robot description container
        N : int, optional
            size of the matries, default is 3

        Returns
        =======
        list of Matrices NxN
        """
        return [zeros(N, N) for i in xrange(robo.NL)]

    @classmethod
    def init_vec(cls, robo, N=3, ext=0):
        """Generates a list of vectors.
        Size of the list is number of links.

        Parameters
        ==========
        robo : Robot
            Instance of robot description container
        N : int, optional
            size of the vectors, default is 3
        ext : int, optional
            additional vector instances over number of links

        Returns
        =======
        list of Matrices Nx1
        """
        return [zeros(N, 1) for i in xrange(robo.NL+ext)]

    @classmethod
    def init_scalar(cls, robo):
        """Generates a list of vars.
        Size of the list is number of links.
        """
        return [0 for i in xrange(robo.NL)]

    @classmethod
    def init_w(cls, robo):
        """Generates a list of vectors for angular velocities.
        Size of the list is number of links + 1.
        The last vector is the base angular velocity
        """
        w = cls.init_vec(robo)
        w.append(robo.w0)
        return w

    @classmethod
    def init_wv_dot(cls, robo):
        """Generates lists of vectors for
        angular and linear accelerations.
        Size of the list is number of links + 1.
        The last vector is the base angular velocity

        Returns
        =======
        vdot : list of Matrices 3x1
        wdot : list of Matrices 3x1
        """
        wdot = cls.init_vec(robo)
        wdot.append(robo.wdot0)
        vdot = cls.init_vec(robo)
        vdot.append(robo.vdot0 - robo.G)
        return wdot, vdot

    @classmethod
    def init_U(cls, robo):
        """Generates a list of auxiliary U matrices"""
        U = Init.init_mat(robo)
        # the value for the -1th base frame
        U.append(hat(robo.w0)**2 + hat(robo.wdot0))
        return U

    @classmethod
    def product_combinations(cls, v):
        """Generates 6-vector of different v elements'
        product combinations

        Parameters
        ==========
        v : Matrix 3x1
            vector

        Returns
        =======
        product_combinations : Matrix 6x1
        """
        return Matrix([v[0]*v[0], v[0]*v[1], v[0]*v[2],
                     v[1]*v[1], v[1]*v[2], v[2]*v[2]])

def hat(v):
    """Generates vectorial preproduct matrix

    Parameters
    ==========
    v : Matrix 3x1
        vector

    Returns
    =======
    hat : Matrix 3x3
    """
    return Matrix([[0, - v[2], v[1]],
                   [v[2], 0, - v[0]],
                   [ - v[1], v[0], 0]])

def l2str(list_var, spacing=7):
    """Converts a list into string, that will be
    written into the text table.

    Parameters
    ==========
    list_var : list
        List to be converted
    spacing : int, optional
        Defines the size of one cell of the table

    Returns
    =======
    s : string
        String representation

    Notes
    =====
    l2str([1, 2, 3]) will be converted into '1      2      3      '
    """
    s = ''
    for i in list_var:
        s += str(i) + ' '*(spacing-len(str(i)))
    return s

def get_trig_couple_names(sym):
    names_s = find_trig_names(sym, r'S', 1)
    names_c = find_trig_names(sym, r'C', 1)
    return  names_c, names_s


def find_trig_names(sym, pref=r'', pref_len=0, post=r'', post_len=0):
    search_res = re.findall(pref + r'[AGm0-9]*'+ post, str(sym))
    if post_len == 0:
        return set([s[pref_len:] for s in search_res])
    else:
        return set([s[pref_len:-post_len] for s in search_res])

def get_trig_pow_names(sym, min_pow=2):
    post = r'\*\*[{0}-9]'.format(min_pow)
    names_s = find_trig_names(sym, r'S', 1, post, 3 )
    names_c = find_trig_names(sym, r'C', 1, post, 3 )
    return names_c & names_s

def get_max_coef_list(sym, x):
    return [get_max_coef_mul(s, x) for s in Add.make_args(sym)]

def get_max_coef(sym, x):
    return Add.fromiter(get_max_coef_mul(s, x) for s in Add.make_args(sym))

def get_max_coef_mul(sym, x):
    """
    """
    k, ex = x.as_coeff_Mul()
    coef = sym / k
    pow_x = ex.as_powers_dict()
    pow_c = coef.as_powers_dict()
    pow_c[-1] = 0
    for a, pa in pow_x.iteritems():
        na = -a
        if a in pow_c and pow_c[a] >= pa:
            pow_c[a] -= pa
        elif na in pow_c and pow_c[na] >= pa:
            pow_c[na] -= pa
            if pa % 2:
                pow_c[-1] += 1
        else:
            return ZERO
    return Mul.fromiter(c**p for c, p in pow_c.iteritems())

def ang_sum(np1, np2, nm1, nm2):
    np2, nm1 = reduce_str(np2, nm1)
    np1, nm2 = reduce_str(np1, nm2)
    if len(nm1) + len(nm2) == 0: return np1 + np2
    else: return np1 + np2 + 'm' + nm1 + nm2

def get_pos_neg(s):
    if s.find('m') != -1:
        return s.split('m')[0], s.split('m')[1]
    else:
        return s, ''

def reduce_str(s1, s2):
    for j, char in enumerate(s1):
        i = s2.find(char)
        if s2.find(char) != -1:
            s2 = s2[:i] + s2[i+1:]
            s1 = s1[:j] + s1[j+1:]
    return s1, s2

def CS_syms(name):
    if isinstance(name, str) and name[0] == 'm':
        C, S = var('C{0}, S{0}'.format(name[1:]))
        return C, -S
    else:
        return var('C{0}, S{0}'.format(name))

def sym_less(A, B):
    A_measure = A.count_ops()
    B_measure = B.count_ops()
    return  A_measure < B_measure

def get_angles(expr):
    angles_s = set()
    for s in expr.atoms(sin):
        angles_s |= set(s.args)
    angles_c = set()
    for c in expr.atoms(cos):
        angles_c |= set(c.args)
    return angles_s & angles_c

def cancel_terms(sym, X, coef):
    if coef.is_Add:
        for arg_c in coef.args:
            sym = cancel_terms(sym, X, arg_c)
    else:
        terms = Add.make_args(sym)
        return Add.fromiter(t for t in terms if t != X*coef)

def trigonometric_info(sym):
    if not sym.has(sin) and not sym.has(cos):
        short_form = True
        c_names, s_names = get_trig_couple_names(sym)
        names = c_names & s_names
    else:
        short_form = False
        names = get_angles(sym)
    return names, short_form


class Symoro:
    """Symbol manager, responsible for symbol replacing, file writing."""
    def __init__(self, file_out='disp'):
        """Default values correspond to empty dictionary and screen output.
        """
        self.file_out = file_out
        """Output descriptor. Can be None, 'disp', file
        defines the output destination"""
        self.sydi = {}
        """Dictionary. All the substitutions are saved in it"""
        self.revdi = {}
        """Dictionary. Revers to the self.sydi"""
        self.order_list = []
        """keeps the order of variables to be compute"""

    def simp(self, sym):
        sym = factor(sym)
        new_sym = ONE
        for e in Mul.make_args(sym):
            if e.is_Pow:
                e, p = e.args
            else:
                p = 1
            e = self.C2S2_simp(e)
            e = self.CS12_simp(e)
            new_sym *= e**p
        return new_sym

    def C2S2_simp(self, sym):
        """
        Example
        =======
        >> print C2S2_simp(sympify("-C**2*RL + S*(D - RL*S)"))
        D*S - RL
        """
        if not sym.is_Add:
            repl_dict = {}
            for term in sym.atoms(Add):
                repl_dict[term] = self.C2S2_simp(term)
            sym = sym.xreplace(repl_dict)
            return sym
        names, short_form = trigonometric_info(sym)
        for name in names:
            if short_form:
                C, S = CS_syms(name)
            else:
                C, S = cos(name), sin(name)
        return self.try_opt(ONE, None, S**2, C**2, sym)

    def CS12_simp(self, sym):
        """
        Example
        =======
        >> print Symoro().CS12_simp(sympify("C2*C3 - S2*S3"))
        C23 = C2*C3 - S2*S3
        C23
        >> print Symoro().CS12_simp(sympify("C2*S3*R + S2*C3*R"))
        S23 = C2*S3 + S2*C3
        R*S23
        """
        if not sym.is_Add:
            repl_dict = {}
            for term in sym.atoms(Add):
                repl_dict[term] = self.CS12_simp(term)
            sym = sym.xreplace(repl_dict)
            return sym
        names, short_form = trigonometric_info(sym)
        names = list(names)
        names.sort()
        for n1, n2 in combinations(names, 2):
            if short_form:
                C1, S1 = CS_syms(n1)
                C2, S2 = CS_syms(n2)
                np1, nm1 = get_pos_neg(n1)
                np2, nm2 = get_pos_neg(n2)
                n12 = ang_sum(np1, np2, nm1, nm2)
                nm12 = ang_sum(np1, nm2, nm1, np2)
                C12, S12 = CS_syms(n12)
                C1m2, S1m2 = CS_syms(nm12)
            else:
                C1, S1 = cos(n1), sin(n1)
                C2, S2 = cos(n2), sin(n2)
                C12, S12 = cos(n1+n2), sin(n1+n2)
                C1m2, S1m2 = cos(n1-n2), sin(n1-n2)
            sym = self.try_opt(S12, S1m2, S1*C2, C1*S2, sym)
            sym = self.try_opt(C12, C1m2, C1*C2, -S1*S2, sym)
        return sym

    def try_opt(self, A, Am, B, C, old_sym):
        """Replaces B + C by A or B - C by Am.
        Chooses the best option.
        """
        Bc = get_max_coef_list(old_sym, B)
        Cc = get_max_coef_list(old_sym, C)
        if Bc != 0 and Cc != 0:
            coefs = [term for term in Bc if term in Cc]
            if Am != None:
                coefs_n = [term for term in Bc if -term in Cc]
                if len(coefs_n) > len(coefs):
                    C = -C
                    A = Am
                    coefs = coefs_n
            Res = old_sym
            for coef in coefs:
                Res += A*coef - B*coef - C*coef
            if sym_less(Res, old_sym):
                if not A.is_number:
                    self.add_to_dict(A, B + C)
                return Res
        return old_sym

    def add_to_dict(self, new_sym, old_sym):
        """Internal function.
        Extends symbol dictionary by (new_sym, old_sym) pair
        """
        new_sym = sympify(new_sym)
        if new_sym.as_coeff_Mul()[0] == -ONE:
            new_sym = -new_sym
            old_sym = -old_sym
        if new_sym not in self.sydi:
            self.sydi[new_sym] = old_sym
            self.revdi[old_sym] = new_sym
            self.order_list.append(new_sym)
            self.write_equation(new_sym, old_sym)

    def trig_replace(self, M, angle, name):
        """Replaces trigonometric expressions cos(x)
        and sin(x) by CX and SX

        Parameters
        ==========
        M : var or Matrix
            Object of substitution
        angle : var
            symbol that stands for the angle value
        name : int or string
            brief name X for the angle

        Notes
        =====
        The cos(x) and sin(x) will be replaced by CX and SX,
        where X is the name and x is the angle
        """
        if not isinstance(angle, Expr) or angle.is_number:
            return M
        cos_sym, sin_sym = CS_syms(name)
        sym_list = [(cos_sym, cos(angle)), (sin_sym, sin(angle))]
        subs_dict = {}
        for sym, sym_old in sym_list:
            subs_dict[sym_old] = sym
            self.add_to_dict(sym, sym_old)
        for i1 in xrange(M.shape[0]):
            for i2 in xrange(M.shape[1]):
                M[i1, i2] = M[i1, i2].subs(subs_dict)
        return M

    def replace(self, old_sym, name, index='', forced=False):
        """Creates a new symbol for the symbolic expression old_sym.

        Parameters
        ==========
        old_sym : var
            Symbolic expression to be substituted
        name : string or var
            denotion of the expression
        index : int or string, optional
            will be attached to the name. Usualy used for link or joint number.
            Parameter exists for usage convenience
        forced : bool, optional
            If True, the new symbol will be created even if old symbol
            is a simple expression

        Notes
        =====
        Generaly only complex expressions, which contain + - * / ** operations
        will be replaced by a new symbol
        """
        inv_sym = -old_sym
        is_simple = old_sym.is_Atom or inv_sym.is_Atom
        if is_simple and not forced:
            return old_sym
        elif not forced:
            for i in (1, - 1):
                if i * old_sym in self.revdi:
                    return i * self.revdi[i * old_sym]
        new_sym = var(str(name) + str(index))
        self.add_to_dict(new_sym, old_sym)
        return new_sym

    def mat_replace(self, M, name, index='',
                    forced=False, skip=0, symmet=False):
        """Replaces each element in M by symbol

        Parameters
        ==========
        M : Matrix
            Object of substitution
        name : string
            denotion of the expression
        index : int or string, optional
            will be attached to the name. Usualy used for link or joint number.
            Parameter exists for usage convenience
        forced : bool, optional
            If True, the new symbol will be created even if old symbol
            is a simple expression
        skip : int, optional
            Number of bottom rows of the matrix, which will be skipped.
            Used in case of Transformation matrix and forced = True.
        symmet : bool, optional
            If true, only for upper triangle part of the matrix
            symbols will be created. The bottom triangle part the
            same symbols will be used


        Returns
        =======
        M : Matrix
            Matrix with all the elements replaced

        Notes
        =====
        -Each element M_ij will be replaced by symbol name + i + j + index
        -There are two ways to use this function (examples):
            1)  >>> A = B+C+...
                >>> symo.mat_replace(A, 'A')
                # for the case when expression B+C+... is too big
            2)  >>> A = symo.mat_replace(B+C+..., 'A')
                # for the case when B+C+... is small enough
        """
        for i1 in xrange(M.shape[0] - skip):
            for i2 in xrange(M.shape[1]):
                if symmet and i2 < i1:
                    M[i1, i2] = M[i2, i1]
                    continue
                if M.shape[1] > 1:
                    name_index = name + str(i1 + 1) + str(i2 + 1)
                else:
                    name_index = name + str(i1 + 1)
                M[i1, i2] = self.replace(M[i1, i2], name_index, index, forced)
        return M

    def unfold(self, expr):
        """Unfold the expression using the dictionary.

        Parameters
        ==========
        expr : symbolic expression
            Symbolic expression to be unfolded

        Returns
        =======
        expr : symbolic expression
            Unfolded expression
        """
        while self.sydi.keys() & expr.atoms():
            expr = expr.subs(self.sydi)
        return expr

    def write_param(self, name, header, param, N):
        """Low-level function for writing the parameters table

        Parameters
        ==========
        name : string
            the name of the table
        header : list
            the table header
        param : callable (int) : list
            returns the list of parameters for
            the particular row of the table
        N : int
            number of lines in the table
        """
        self.write_line(name)
        self.write_line(l2str(header))
        for j in xrange(N):
            self.write_line(l2str(param(j)))
        self.write_line()

    def write_geom_param(self, robo, title=''):
        """Writes the geometric parameters table

        Parameters
        ==========
        robo : Robot
            Instance of the parameter container
        title : string, optional
            The document title. Not used in case of internal using
        """
        if title != '':
            self.write_line(title)
            self.write_line()
        self.write_param('Geometric parameters', robo.get_geom_head(),
                         robo.get_geom_param, robo.NF)

    def write_inert_param(self, robo, name='Dynamic inertia parameters'):
        """Writes the inertia parameters table

        Parameters
        ==========
        robo : Robot
            Instance of the parameter container
        name : string, optional
            The table name. Not used in case of internal using.
        """
        self.write_param(name, robo.get_inert_head(),
                 robo.get_inert_param, robo.NL)

    def write_dynam_param(self, robo, title):
        """Writes the geometric parameters table

        Parameters
        ==========
        robo : Robot
            Instance of the parameter container.
        title : string
            The document title.

        Notes
        =====
        The synamic model generation program can be started with this function
        """
        self.write_line(title)
        self.write_line()
        self.write_geom_param(robo)
        self.write_inert_param(robo)
        self.write_param('External forces and joint parameters',
                         robo.get_ext_dynam_head(),
                         robo.get_ext_dynam_param, robo.NL)
        self.write_param('Base velicities parameters', robo.get_base_vel_head(),
                         robo.get_base_vel, 3)

    def unknown_sep(self, eq, known):
        """If there is a sum inside trigonometric function and
        the atoms are not the subset of 'known',
        this function will replace the trigonometric symbol bu sum,
        trying to separate known and unknown terms
        """
        while True:
            res = False
            trigs = eq.atoms(sin, cos)
            for trig in trigs:
                args = trig.args[0].atoms()
                if args & known and not args <= known and trig in self.sydi:
                    eq = eq.subs(trig, self.sydi[trig])
                    res = True
            if not res:
                break
        return eq

    def write_equation(self, A, B):
        """Writes the equation A = B into the output

        Parameters
        ==========
        A : expression or var
            left-hand side of the equation.
        B : expression or var
            right-hand side of the equation
        """
        self.write_line(str(A) + ' = ' + str(B))

    def write_line(self, line=''):
        """Writes string data into tha output with new line symbol

        Parameters
        ==========
        line : string, optional
            Data to be written. If empty, it adds an empty line
        """
        if self.file_out == 'disp':
            print line
        elif self.file_out != None:
            self.file_out.write(str(line) + '\n')

    def file_open(self, robo, ext):
        """
        Initialize file stream

        Parameters
        ==========
        robo : Robot instance
            provides the robot's name
        ext : string
            provides the file name extention
        """
        self.file_out = open('models\\' + robo.name + '_' + ext + '.txt', 'w')

    def gen_fheader(self, name, *args):
        fun_head = []
        fun_head.append('def %s_func(*args):\n' % name)
        imp_s = 'from numpy import sin, cos, sign, array, arctan2 as atan2, sqrt\n'
        fun_head.append('    %s' % imp_s)
        for i, var_list in enumerate(args):
            v_str_list = self.convert_syms(args[i], True)
            fun_head.append('    %s=args[%s]\n' % (v_str_list, i))
        return fun_head

    def convert_syms(self, syms, rpl_liter=False):
        """Converts 'syms' structure to sintactically correct string

        Parameters
        ==========
        syms: list, Matrix or tuple of them
        rpl_liter: bool
            if true, all literals will be replaced with 'NULx' name.
            It is done to evoid expression like [x, 0] = args[1]
            Because it will cause exception of assigning to literal
        """
        if isinstance(syms, tuple):
            syms = [self.convert_syms(item, rpl_liter) for item in syms]
            res = ''
            for i, s in enumerate(syms):
                res += s
                if i < len(syms) - 1:
                    res += ', '
            return res
        elif isinstance(syms, Matrix):
            res = '['
            for i in xrange(syms.shape[0]):
                res += self.convert_syms(list(syms[i, :]), rpl_liter)
                if i < syms.shape[0] - 1:
                    res += ', '
            res += ']'
            return res
        elif isinstance(syms, list):
            row = '['
            for j, s in enumerate(syms):
                if rpl_liter and sympify(s).is_number:
                    row += 'NUL%s' % j
                else:
                    row += str(s)
                if j < len(syms) - 1:
                    row += ', '
            row += ']'
            return row

    def extract_syms(self, syms):
        """ returns set of all symbols from list or matrix
        or tuple of them
        """
        if isinstance(syms, tuple):
            atoms = (self.extract_syms(item) for item in syms)
            return reduce(set.__or__, atoms, set())
        elif isinstance(syms, Matrix):
            return self.extract_syms(list(syms))
        elif isinstance(syms, list):
            atoms = (s.atoms(Symbol) for s in syms if isinstance(s, Expr))
            return reduce(set.__or__, atoms, set())

    def sift_syms(self, rq_syms, wr_syms):
        """Returns ordered list of variables to be compute
        """
        order_list = []   # vars that are defined in sydi
        for s in reversed(self.order_list):
            if s in rq_syms:
                order_list.insert(0, s)
                s_val = self.sydi[s]
                if isinstance(s_val, Expr):
                    atoms = s_val.atoms(Symbol)
                    rq_syms |= {s for s in atoms if not s.is_number}
        rq_vals = [s for s in rq_syms if not (s in self.sydi or s in wr_syms)]
            # required vars that are not defined in sydi
            # will be set to '1.'
        return rq_vals + order_list

    def gen_fbody(self, name, to_return, wr_syms):
        """Generates list of string statements of the function that
        computes symbolf from to_return.  wr_syms are considered to
        be known
        """
        syms = self.extract_syms(to_return)
            # final symbols to be compute
        order_list = self.sift_syms(syms, wr_syms)
            # defines order of computation
        fun_body = []
            # list of instructions in final function
        multival = False
            # will be switched to true when branching detected
        space = '    '
        folded = 1
            # size of indentation; = 1 + number of 'for' statements
        for s in order_list:
            if s not in self.sydi:
                item = '%s%s=1.\n' % (space * folded, s)
            elif isinstance(self.sydi[s], tuple):
                multival = True
                item = '%sfor %s in %s:\n' % (space * folded, s, self.sydi[s])
                folded += 1
            else:
                item = '%s%s=%s\n' % (space * folded, s, self.sydi[s])
            fun_body.append(item)
        ret_expr = self.convert_syms(to_return)
        if multival:
            fun_body.insert(0, '    %s_result=[]\n' % (name))
            item = '%s%s_result.append(%s)\n' % (space*folded, name, ret_expr)
        else:
            item = '    %s_result=%s\n' % (name, ret_expr)
        fun_body.append(item)
        fun_body.append('    return %s_result\n' % (name))
        return fun_body

    def gen_func(self, name, to_return, *args):
        """ Returns function that computes what is in to_return
        using *args as arguments

         Parameters
        ==========
        name : string
            Future function's name, must be different for
            different fucntions
        to_return : list, Matrix or tuple of them
            Determins the shape of the output and symbols inside it
        *args: any number of lists, Matrices or tuples of them
            Determins the shape of the input and symbols
            names to assigned

        Notes
        =====
        -All unassigned used symbols will be set to '1.0'.
        -This function must be called only after the model that
        computes symbols in to_compute have been generated.
        """
        fun_head = self.gen_fheader(name, *args)
        wr_syms = self.extract_syms(args) # set of defined symbols
        fun_body = self.gen_fbody(name, to_return, wr_syms)
        fun_string = "".join(fun_head + fun_body)
        print fun_string
        exec fun_string
        return eval('%s_func'%name)

#################################################################
#testing and debug section
#to be removed later

#symo = Symoro()

# d = sympify("C2*C3*C4**2*C5**2*C6**4*D3**2*RL4*S5 + 2*C2*C3*C4**2*C5**2*C6**2*D3**2*RL4*S5*S6**2 + C2*C3*C4**2*C5**2*D3**2*RL4*S5*S6**4 + C2*C3*C4**2*C6**4*D3**2*RL4*S5**3 + 2*C2*C3*C4**2*C6**2*D3**2*RL4*S5**3*S6**2 + C2*C3*C4**2*D3**2*RL4*S5**3*S6**4 + C2*C3*C5**2*C6**4*D3**2*RL4*S4**2*S5 + 2*C2*C3*C5**2*C6**2*D3**2*RL4*S4**2*S5*S6**2 + C2*C3*C5**2*D3**2*RL4*S4**2*S5*S6**4 + C2*C3*C6**4*D3**2*RL4*S4**2*S5**3 + 2*C2*C3*C6**2*D3**2*RL4*S4**2*S5**3*S6**2 + C2*C3*D3**2*RL4*S4**2*S5**3*S6**4 - C3*C4**2*C5**2*C6**4*D3*RL4**2*S23*S5 - 2*C3*C4**2*C5**2*C6**2*D3*RL4**2*S23*S5*S6**2 - C3*C4**2*C5**2*D3*RL4**2*S23*S5*S6**4 - C3*C4**2*C6**4*D3*RL4**2*S23*S5**3 - 2*C3*C4**2*C6**2*D3*RL4**2*S23*S5**3*S6**2 - C3*C4**2*D3*RL4**2*S23*S5**3*S6**4 - C3*C5**2*C6**4*D3*RL4**2*S23*S4**2*S5 - 2*C3*C5**2*C6**2*D3*RL4**2*S23*S4**2*S5*S6**2 - C3*C5**2*D3*RL4**2*S23*S4**2*S5*S6**4 - C3*C6**4*D3*RL4**2*S23*S4**2*S5**3 - 2*C3*C6**2*D3*RL4**2*S23*S4**2*S5**3*S6**2 - C3*D3*RL4**2*S23*S4**2*S5**3*S6**4")
# d = sympify("C2**5*C3**3*C4**2*D3**2*RL4*S5 - C2**5*C3**3*C4**2*D3*RL4**2*S3*S5 + C2**5*C3**3*D3**2*RL4*S4**2*S5 - C2**5*C3**3*D3*RL4**2*S3*S4**2*S5 + C2**5*C3*C4**2*D3**2*RL4*S3**2*S5 - C2**5*C3*C4**2*D3*RL4**2*S3**3*S5 + C2**5*C3*D3**2*RL4*S3**2*S4**2*S5 - C2**5*C3*D3*RL4**2*S3**3*S4**2*S5 - C2**4*C3**4*C4**2*D3*RL4**2*S2*S5 - C2**4*C3**4*D3*RL4**2*S2*S4**2*S5 - C2**4*C3**2*C4**2*D3*RL4**2*S2*S3**2*S5 - C2**4*C3**2*D3*RL4**2*S2*S3**2*S4**2*S5 + 2*C2**3*C3**3*C4**2*D3**2*RL4*S2**2*S5 - 2*C2**3*C3**3*C4**2*D3*RL4**2*S2**2*S3*S5 + 2*C2**3*C3**3*D3**2*RL4*S2**2*S4**2*S5 - 2*C2**3*C3**3*D3*RL4**2*S2**2*S3*S4**2*S5 + 2*C2**3*C3*C4**2*D3**2*RL4*S2**2*S3**2*S5 - 2*C2**3*C3*C4**2*D3*RL4**2*S2**2*S3**3*S5 + 2*C2**3*C3*D3**2*RL4*S2**2*S3**2*S4**2*S5 - 2*C2**3*C3*D3*RL4**2*S2**2*S3**3*S4**2*S5 - 2*C2**2*C3**4*C4**2*D3*RL4**2*S2**3*S5 - 2*C2**2*C3**4*D3*RL4**2*S2**3*S4**2*S5 - 2*C2**2*C3**2*C4**2*D3*RL4**2*S2**3*S3**2*S5 - 2*C2**2*C3**2*D3*RL4**2*S2**3*S3**2*S4**2*S5 + C2*C3**3*C4**2*D3**2*RL4*S2**4*S5 - C2*C3**3*C4**2*D3*RL4**2*S2**4*S3*S5 + C2*C3**3*D3**2*RL4*S2**4*S4**2*S5 - C2*C3**3*D3*RL4**2*S2**4*S3*S4**2*S5 + C2*C3*C4**2*D3**2*RL4*S2**4*S3**2*S5 - C2*C3*C4**2*D3*RL4**2*S2**4*S3**3*S5 + C2*C3*D3**2*RL4*S2**4*S3**2*S4**2*S5 - C2*C3*D3*RL4**2*S2**4*S3**3*S4**2*S5 - C3**4*C4**2*D3*RL4**2*S2**5*S5 - C3**4*D3*RL4**2*S2**5*S4**2*S5 - C3**2*C4**2*D3*RL4**2*S2**5*S3**2*S5 - C3**2*D3*RL4**2*S2**5*S3**2*S4**2*S5")
# print 'det\n', d
# d = symo.C4S4_simp(d)
# print 'C4S4\n', d
# d = symo.C2S2_simp(d)
# print 'C2S2\n', d
# d = symo.CS12_simp(d)
# print 'CS12\n', d
# d = symo.poly_simp(d)
# print 'poly\n', d.factor()

# E = sympify("C3*D3*RL4*S5*(C5**2*(C2*D3*(C4**2*(C6**4 + S6**4) + C6**2*(2*C4**2*S6**2 + S4**2*(C6**2 + 2*S6**2))) - C4**2*RL4*S23*S6**4) + C6**4*(-C4**2 - S4**2)*(C5**2*RL4*S23 - S5**2*(C2*D3 - RL4*S23)) + S6**2*(-2*C6**2*(RL4*S23*(C4**2*C5**2 + C4**2*S5**2 + C5**2*S4**2) - S5**2*(C2*C4**2*D3 + S4**2*(C2*D3 - RL4*S23))) - S6**2*(C2*D3 - RL4*S23)*(-C4**2*S5**2 + S4**2*(-C5**2 - S5**2))))")
# print E
# print E.expand()
# E2 = Symoro().C4S4_simp(E)
# print E2
# E3 = Symoro().C2S2_simp(E2)
# print E3



# print div_cancel(sympify("-C23*RL4**2*S23*S5"), sympify("-RL4*S23"))
# print ex
#ex = sympify("C23*RL4**2*S23*S5*(d-f)**5")
#ex2 = sympify("-RL4*S23*(-d+f)**4")
#print get_max_coef(ex, ex2)
#print get_max_coef(ex, ex2)
#def a():
#    get_max_coef(ex, ex2)
#def b():
#    for i in xrange(100):
#        get_max_coef(ex, ex2)
#
#from timeit import timeit
# timeit(a, number = 1)
#print timeit(a, number = 1000)
#print timeit(b, number = 1000)


#print Symoro().CS12_simp(sympify("C2*S3*R + S2*C3*R"))
# # #
#import profile
# #
#profile.run('a()', sort = 'cumtime')
#profile.run('b()', sort = 'cumtime')
# from timeit import timeit
#d = sympify("S1**2 + S1**2*C1 + C1**2 + C1**3 + C1**4")
#print Symoro().C2S2_simp(d)
#print Symoro().CS12_simp(sympify("C2*D3*S3m78 - C2m7*D8*S3 - C3*D8*S2m7 - C3m78*D3*S2 + D2*S3"))
#def a():
#    Symoro().CS12_simp(sympify("-a1*sin(th2+th1)*sin(th3)*cos(th1) - a1*cos(th1)*cos(th2+th1)*cos(th3)"))
#print timeit(a, number = 10)