import numpy as _np
import scipy.sparse as _sp
import os
from ..lattice import lattice_basis
import warnings

class GeneralBasisWarning(Warning):
	pass


def process_map(map,q):
	map = _np.asarray(map,dtype=_np.int32)
	i_map = map.copy()
	i_map[map<0] = -(i_map[map<0] + 1) # site mapping
	s_map = map < 0 # sites with spin-inversion

	sites = _np.arange(len(map),dtype=_np.int32)
	order = sites.copy()

	if _np.any(_np.sort(i_map)-order):
		raise ValueError("map must be a one-to-one site mapping.")

	per = 0
	group = [tuple(order)]
	while(True):
		sites[s_map] = -(sites[s_map]+1)
		sites = sites[i_map]
		per += 1
		group.append(tuple(sites))
		if _np.array_equal(order,sites):
			break

	if per == 1:
		warnings.warn("identity mapping found in set of transformations.",GeneralBasisWarning,stacklevel=5)

	return map,per,q,set(group)

def check_symmetry_maps(item1,item2):
	grp1 = item1[1][-1]
	map1 = item1[1][0]
	block1 = item1[0]

	i_map1 = map1.copy()
	i_map1[map1<0] = -(i_map1[map1<0] + 1) # site mapping
	s_map1 = map1 < 0 # sites with spin-inversion		

	grp2 = item2[1][-1]
	map2 = item2[1][0]
	block2 = item2[0]

	i_map2 = map2.copy()
	i_map2[map2<0] = -(i_map2[map2<0] + 1) # site mapping
	s_map2 = map2 < 0 # sites with spin-inversion

	if grp1 == grp2:
		warnings.warn("mappings for block {} and block {} produce the same symmetry.".format(block1,block2),GeneralBasisWarning,stacklevel=5)

	sites1 = _np.arange(len(map1))
	sites2 = _np.arange(len(map2))

	sites1[s_map1] = -(sites1[s_map1]+1)
	sites1 = sites1[i_map1]
	sites1[s_map2] = -(sites1[s_map2]+1)
	sites1 = sites1[i_map2]

	sites2[s_map2] = -(sites2[s_map2]+1)
	sites2 = sites2[i_map2]
	sites2[s_map1] = -(sites2[s_map1]+1)
	sites2 = sites2[i_map1]

	if not _np.array_equal(sites1,sites2):
		warnings.warn("using non-commuting symmetries can lead to unwanted behaviour of general basis, make sure that quantum numbers are invariant under non-commuting symmetries!",GeneralBasisWarning,stacklevel=5)

class basis_general(lattice_basis):
	def __init__(self,N,**kwargs):
		self._unique_me = True
		self._check_pcon = None
		self._made_basis = False # keeps track of whether the basis has been made

		if self.__class__ is basis_general:
			raise TypeError("general_basis class is not to be instantiated.")

		kwargs = {key:value for key,value in kwargs.items() if value is not None}
		
		# if not kwargs:
		# 	raise ValueError("require at least one map.")

		n_maps = len(kwargs)

		if n_maps > 32:
			raise ValueError("general basis can only support up to 32 symmetries.")

		if n_maps>0:
			self._conserved='custom symmeries'
		else:
			self._conserved=''

		if any((type(map) is not tuple) and (len(map)!=2) for map in kwargs.values()):
			raise ValueError("blocks must contain tuple: (map,q).")

		kwargs = {block:process_map(*item) for block,item in kwargs.items()}
		
		sorted_items = sorted(kwargs.items(),key=lambda x:x[1][1])
		sorted_items.reverse()

		self._blocks = {block:((-1)**q if per==2 else q) for block,(_,per,q,_) in sorted_items}
		self._maps_dict = {block:map for block,(map,_,_,_) in sorted_items}
		remove_index = []
		for i,item1 in enumerate(sorted_items[:-1]):
			if item1[1][1] == 1:
				remove_index.append(i)
			for j,item2 in enumerate(sorted_items[i+1:]):
				check_symmetry_maps(item1,item2)

		remove_index.sort()

		if sorted_items:
			blocks,items = zip(*sorted_items)
			items = list(items)

			for i in remove_index:
				items.pop(i)

			n_maps = len(items)
			maps,pers,qs,_ = zip(*items)

			self._maps = _np.vstack(maps)
			self._qs   = _np.asarray(qs,dtype=_np.int32)
			self._pers = _np.asarray(pers,dtype=_np.int32)

			if any(map.ndim != 1 for map in self._maps[:]):
				raise ValueError("maps must be a 1-dim array/list of integers.")

			if any(map.shape[0] != N for map in self._maps[:]):
				raise ValueError("size of map is not equal to N.")

			if self._maps.shape[0] != self._qs.shape[0]:
				raise ValueError("number of maps must be the same as the number of quantum numbers provided.")

			for j in range(n_maps-1):
				for i in range(j+1,n_maps,1):
					if _np.all(self._maps[j]==self._maps[i]):
						ValueError("repeated map in maps list.")
		else:
			self._maps = _np.array([[]],dtype=_np.int32)
			self._qs   = _np.array([],dtype=_np.int32)
			self._pers = _np.array([],dtype=_np.int32)

		nmax = self._pers.prod()
		self._n_dtype = _np.min_scalar_type(nmax)

	@property
	def description(self):
		"""str: information about `basis` object."""
		blocks = ""

		for symm in self._blocks:
			blocks += symm+" = {"+symm+"}, "

		blocks = blocks.format(**self._blocks)

		if len(self._conserved) == 0:
			symm = "no symmetry"
		elif len(self._conserved) == 1:
			symm = "symmetry"
		else:
			symm = "symmetries"

		string = """general basis for lattice of N = {0} sites containing {5} states \n\t{1}: {2} \n\tquantum numbers: {4} \n\n""".format(self._N,symm,self._conserved,'',blocks,self._Ns)
		string += self.operators
		return string


	def representative(self,states,out=None):
		"""Maps states to their representatives under the `basis` symmetries.

		Parameters
		-----------
		states : array_like(int)
			Fock-basis (z-basis) states to find the representatives of. States are stored in integer representations.
		out : numpy.ndarray(int), optional
			variable to store the representative states in. Must be a numpy.ndarray of same datatype as `basis`, and same shape as `states`. 
				
		Returns
		--------
		array_like(int)
			Representatives under `basis` symmetries, corresponding to `states`.

		Examples
		--------
		
		>>> basis=spin_basis_general(N,Nup=Nup,make_basis=False)
		>>> s = 17
		>>> r = basis.representative(s)
		>>> print(s,r)

		"""

		states=_np.array(states,dtype=self._basis.dtype,ndmin=1)

		if out is None:
			out=_np.zeros(states.shape,dtype=self._basis.dtype)
			self._core.representative(states,out)

			return out.squeeze()

		else:
			if states.shape!=out.shape:
				raise TypeError('states and out must have shape.')
			if out.dtype != self._basis.dtype:
				raise TypeError('out must have same type as basis')
			if not isinstance(out,_np.ndarray):
				raise TypeError('out must be a numpy.ndarray')
			
			self._core.representative(states,out)

			
	def make(self,Ns_block_est=None):
		"""Creates the entire basis by calling the basis constructor.

		Parameters
		-----------
		Ns_block_est: int, optional
			Overwrites the internal estimate of the size of the reduced Hilbert space for the given symmetries. This can be used to help conserve memory if the exact size of the H-space is known ahead of time. 
				
		Returns
		--------
		int
			Total number of states in the (symmetry-reduced) Hilbert space.

		Examples
		--------
		
		>>> N, Nup = 8, 4
		>>> basis=spin_basis_general(N,Nup=Nup,make_basis=False)
		>>> print(basis)
		>>> basis.make()
		>>> print(basis)

		"""

		if Ns_block_est is not None:
			Ns = Ns_block_est
		else:
			Ns = max(self._Ns,1000)


		# preallocate variables
		if self._N<=32:
			basis = _np.zeros(Ns,dtype=_np.uint32)
		elif self._N<=64:
			basis = _np.zeros(Ns,dtype=_np.uint64)
		
		n = _np.zeros(Ns,dtype=self._n_dtype)
		
		# make basis
		if self._count_particles and (self._Np is not None):
			Np_list = _np.zeros_like(basis,dtype=_np.uint8)
			Ns = self._core.make_basis(basis,n,Np=self._Np,count=Np_list)
		else:
			Np_list = None
			Ns = self._core.make_basis(basis,n,Np=self._Np)

		if Ns < 0:
				raise ValueError("estimate for size of reduced Hilbert-space is too low, please double check that transformation mappings are correct or use 'Ns_block_est' argument to give an upper bound of the block size.")

		# sort basis
		if type(self._Np) is int or self._Np is None:
			if Ns > 0:
				self._basis = basis[Ns-1::-1].copy()
				self._n = n[Ns-1::-1].copy()
				if Np_list is not None: self._Np_list = Np_list[Ns-1::-1].copy()
			else:
				self._basis = _np.array([],dtype=basis.dtype)
				self._n = _np.array([],dtype=n.dtype)
				if Np_list is not None: self._Np_list = _np.array([],dtype=Np_list.dtype)
		else:
			ind = _np.argsort(basis[:Ns],kind="heapsort")[::-1]
			self._basis = basis[ind].copy()
			self._n = n[ind].copy()
			if Np_list is not None: self._Np_list = Np_list[ind].copy()


		self._Ns=Ns

		self._index_type = _np.min_scalar_type(-self._Ns)
		self._reduce_n_dtype()

		self._made_basis = True





	def _reduce_n_dtype(self):
		if len(self._n)>0:
			self._n_dtype = _np.min_scalar_type(self._n.max())
			self._n = self._n.astype(self._n_dtype)


	def _Op(self,opstr,indx,J,dtype):

		if not self._made_basis:
			raise AttributeError('this function requires the basis to be constructed first; use basis.make().')

		indx = _np.asarray(indx,dtype=_np.int32)

		if len(opstr) != len(indx):
			raise ValueError('length of opstr does not match length of indx')

		if _np.any(indx >= self._N) or _np.any(indx < 0):
			raise ValueError('values in indx falls outside of system')

		extra_ops = set(opstr) - self._allowed_ops
		if extra_ops:
			raise ValueError("unrecognized characters {} in operator string.".format(extra_ops))

		if self._Ns <= 0:
			return _np.array([],dtype=dtype),_np.array([],dtype=self._index_type),_np.array([],dtype=self._index_type)
	
		col = _np.zeros(self._Ns,dtype=self._index_type)
		row = _np.zeros(self._Ns,dtype=self._index_type)
		ME = _np.zeros(self._Ns,dtype=dtype)

		self._core.op(row,col,ME,opstr,indx,J,self._basis,self._n)

		mask = _np.logical_not(_np.logical_or(_np.isnan(ME),_np.abs(ME)==0.0))
		col = col[mask]
		row = row[mask]
		ME = ME[mask]

		return ME,row,col


	def Op_bra_ket(self,opstr,indx,J,dtype,ket_states,reduce_output=True):
		"""Finds bra states which connect given ket states by operator from a site-coupling list and an operator string.

		Given a set of ket states :math:`|s\\rangle`, the function returns the bra states :math:`\\langle s'|` which connect to them through an operator, together with the corresponding matrix elements.

		Notes
		-----
			* Similar to `Op` but instead of returning the matrix indices (row,col), it returns the states (bra,ket) in integer representation. 
			* Does NOT require the full basis (see `basis` optional argument `make_basis`). 
			* If a state from `ket_states` does not have a non-zero matrix element, it is removed from the returned list. See otional argument `reduce_output`.

		Parameters
		-----------
		opstr : str
			Operator string in the lattice basis format. For instance:

			>>> opstr = "zz"
		indx : list(int)
			List of integers to designate the sites the lattice basis operator is defined on. For instance:
			
			>>> indx = [2,3]
		J : scalar
			Coupling strength.
		dtype : 'type'
			Data type (e.g. numpy.float64) to construct the matrix elements with.
		ket_states : numpy.ndarray(int)
			Ket states in integer representation. Must be of same data type as `basis`.
		reduce_output: bool, optional
			If set to `True`, the retured arrays have the same size as `ket_states`; If set to `False` zeros are purged.

		Returns
		--------
		tuple 
			`(ME,bra,ket)`, where
				* numpy.ndarray(scalar): `ME`: matrix elements of type `dtype`, which connects the ket and bra states.
				* numpy.ndarray(int): `bra`: bra states, obtained by applying the matrix representing the operator in the lattice basis,
					to the ket states, such that `bra[i]` corresponds to `ME[i]` and connects to `ket[i]`.
				* numpy.ndarray(int): `ket`: ket states, such that `ket[i]` corresponds to `ME[i]` and connects to `bra[i]`.

			
		Examples
		--------

		>>> J = 1.41
		>>> indx = [2,3]
		>>> opstr = "zz"
		>>> dtype = np.float64
		>>> ME, bra, ket = Op_bra_ket(opstr,indx,J,dtype,ket_states)

		"""

		
		indx = _np.asarray(indx,dtype=_np.int32)
		ket_states=_np.array(ket_states,dtype=self._basis.dtype,ndmin=1)

		if len(opstr) != len(indx):
			raise ValueError('length of opstr does not match length of indx')

		if _np.any(indx >= self._N) or _np.any(indx < 0):
			raise ValueError('values in indx falls outside of system')

		extra_ops = set(opstr) - self._allowed_ops
		if extra_ops:
			raise ValueError("unrecognized characters {} in operator string.".format(extra_ops))

	
		bra = _np.zeros_like(ket_states) # row
		ME = _np.zeros(ket_states.shape[0],dtype=dtype)

		self._core.op_bra_ket(ket_states,bra,ME,opstr,indx,J,self._Np)
		
		if reduce_output: 
			# remove nan's matrix elements
			mask = _np.logical_not(_np.logical_or(_np.isnan(ME),_np.abs(ME)==0.0))
			bra = bra[mask]
			ket_states = ket_states[mask]
			ME = ME[mask]
		else:
			mask = _np.isnan(ME)
			ME[mask] = 0.0

		return ME,bra,ket_states



	def get_proj(self,dtype):
		"""Calculates transformation/projector from symmetry-reduced basis to full (symmetry-free) basis.

		Notes
		-----
		Particularly useful when a given operation canot be carried away in the symmetry-reduced basis
		in a straightforward manner.

		Parameters
		-----------
		dtype : 'type'
			Data type (e.g. numpy.float64) to construct the projector with.
		sparse : bool, optional
			Whether or not the output should be in sparse format. Default is `True`.
		
		Returns
		--------
		scipy.sparse.csr_matrix
			Transformation/projector between the symmetry-reduced and the full basis.

		Examples
		--------

		>>> P = get_proj(np.float64,pcon=False)
		>>> print(P.shape)

		"""

		if not self._made_basis:
			raise AttributeError('this function requires the basis to be constructed first; use basis.make().')

		c = _np.ones_like(self._basis,dtype=dtype)
		sign = _np.ones_like(self._basis,dtype=_np.int8)
		c[:] = self._n[:]
		c *= self._pers.prod()
		_np.sqrt(c,out=c)
		_np.power(c,-1,out=c)
		index_type = _np.min_scalar_type(-(self._sps**self._N))
		col = _np.arange(self._Ns,dtype=index_type)
		row = _np.arange(self._Ns,dtype=index_type)
		return self._core.get_proj(self._basis,dtype,sign,c,row,col)

	def get_vec(self,v0,sparse=True):
		"""Transforms state from symmetry-reduced basis to full (symmetry-free) basis.

		Notes
		-----
		Particularly useful when a given operation canot be carried away in the symmetry-reduced basis
		in a straightforward manner.

		Supports parallelisation to multiple states listed in the columns.

		Parameters
		-----------
		v0 : numpy.ndarray
			Contains in its columns the states in the symmetry-reduced basis.
		sparse : bool, optional
			Whether or not the output should be in sparse format. Default is `True`.
		
		Returns
		--------
		numpy.ndarray
			Array containing the state `v0` in the full basis.

		Examples
		--------

		>>> v_full = get_vec(v0)
		>>> print(v_full.shape, v0.shape)

		"""

		if not self._made_basis:
			raise AttributeError('this function requires the basis to be cosntructed first, see basis.make().')

		if not hasattr(v0,"shape"):
			v0 = _np.asanyarray(v0)

		squeeze = False

		if v0.ndim == 1:
			shape = (self._sps**self._N,1)
			v0 = v0.reshape((-1,1))
			squeeze = True
		elif v0.ndim == 2:
			shape = (self._sps**self._N,v0.shape[1])
		else:
			raise ValueError("excpecting v0 to have ndim at most 2")

		if self._Ns <= 0:
			if sparse:
				return _sp.csr_matrix(([],([],[])),shape=(self._sps**self._N,0),dtype=v0.dtype)
			else:
				return _np.zeros((self._sps**self._N,0),dtype=v0.dtype)

		if v0.shape[0] != self._Ns:
			raise ValueError("v0 shape {0} not compatible with Ns={1}".format(v0.shape,self._Ns))

		if _sp.issparse(v0): # current work around for sparse states.
			# return self.get_proj(v0.dtype).dot(v0)
			raise ValueError

		if not v0.flags["C_CONTIGUOUS"]:
			v0 = _np.ascontiguousarray(v0)

		if sparse:
			# current work-around for sparse
			return self.get_proj(v0.dtype).dot(_sp.csr_matrix(v0))
		else:
			v_out = _np.zeros(shape,dtype=v0.dtype,)
			self._core.get_vec_dense(self._basis,self._n,v0,v_out)
			if squeeze:
				return  _np.squeeze(v_out)
			else:
				return v_out	

	def _check_symm(self,static,dynamic,photon_basis=None):
		if photon_basis is None:
			basis_sort_opstr = self._sort_opstr
			static_list,dynamic_list = self._get_local_lists(static,dynamic)
		else:
			basis_sort_opstr = photon_basis._sort_opstr
			static_list,dynamic_list = photon_basis._get_local_lists(static,dynamic)


		static_blocks = {}
		dynamic_blocks = {}
		for block,map in self._maps_dict.items():
			key = block+" symm"
			odd_ops,missing_ops = _check_symm_map(map,basis_sort_opstr,static_list)
			if odd_ops or missing_ops:
				static_blocks[key] = (tuple(odd_ops),tuple(missing_ops))

			odd_ops,missing_ops = _check_symm_map(map,basis_sort_opstr,dynamic_list)
			if odd_ops or missing_ops:
				dynamic_blocks[key] = (tuple(odd_ops),tuple(missing_ops))


		return static_blocks,dynamic_blocks


def _check_symm_map(map,sort_opstr,operator_list):
	missing_ops=[]
	odd_ops=[]
	for op in operator_list:
		opstr = str(op[0])
		indx  = list(op[1])
		J     = op[2]
		for j,ind in enumerate(op[1]):
			i = map[ind]
			if i < 0:
				if opstr[j] == "n":
					odd_ops.append(op)

				J *= (-1 if opstr[j] in ["z","y"] else 1)
				opstr = opstr.replace("+","#").replace("-","+").replace("#","-")
				i = -(i+1)

			indx[j] = i

		new_op = list(op)
		new_op[0] = opstr
		new_op[1] = indx
		new_op[2] = J

		new_op = sort_opstr(new_op)
		if not (new_op in operator_list):
			missing_ops.append(new_op)

	return odd_ops,missing_ops







