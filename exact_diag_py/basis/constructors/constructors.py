import basis_ops
from numpy import dtype as _dtype

__all__=['op_m','op_z','op_p','op_pz','op_p_z','op_t','op_t_z','SpinOp']



_type_conv = {'f': 's', 'd': 'd', 'F': 'c', 'D': 'z'}

_basis_op_errors={1:"opstr character not recognized.",
									-1:"attemping to use real hamiltonian with complex matrix elements."}








class FortranError(Exception):
	# this class defines an exception which can be raised whenever there is some sort of error which we can
	# see will obviously break the code. 
	def __init__(self,message):
		self.message=message
	def __str__(self):
		return self.message




def op_m(basis,opstr,indx,dtype):

	dtype = _dtype(dtype)
	char = _type_conv[dtype.char]
	fortran_op = basis_ops.__dict__[char+"_m_op"]
	col,ME,error = fortran_op(basis,opstr,indx)
	if error != 0: raise FortranError(_basis_op_errors[error])

	return ME,col
		



def op_z(N,basis,opstr,indx,L,dtype,**blocks):
	zblock=blocks.get("zblock")

	dtype = _dtype(dtype)
	char = _type_conv[dtype.char]
	fortran_op = basis_ops.__dict__[char+"_z_op"]

	col,ME,error = fortran_op(N,basis,opstr,indx,L,zblock)

	if error != 0: raise FortranError(_basis_op_errors[error])

	return ME,col



def op_p(N,basis,opstr,indx,L,dtype,**blocks):
	pblock=blocks.get("pblock")

	dtype = _dtype(dtype)
	char = _type_conv[dtype.char]
	fortran_op = basis_ops.__dict__[char+"_p_op"]
	col,ME,error = fortran_op(N,basis,opstr,indx,L,pblock)

	if error != 0: raise FortranError(_basis_op_errors[error])

	return ME,col



def op_pz(N,basis,opstr,indx,L,dtype,**blocks):
	pzblock=blocks.get("pzblock")

	dtype = _dtype(dtype)
	char = _type_conv[dtype.char]
	fortran_op = basis_ops.__dict__[char+"_pz_op"]
	col,ME,error = fortran_op(N,basis,opstr,indx,L,pzblock)

	if error != 0: raise FortranError(_basis_op_errors[error])

	return ME,col



def op_p_z(N,basis,opstr,indx,L,dtype,**blocks):
	zblock=blocks.get("zblock")
	pblock=blocks.get("pblock")

	dtype = _dtype(dtype)
	char = _type_conv[dtype.char]
	fortran_op = basis_ops.__dict__[char+"_p_z_op"]
	col,ME,error = fortran_op(N,basis,opstr,indx,L,pblock,zblock)
	if error != 0: raise FortranError(_basis_op_errors[error])

	return ME,col





def op_t(N,m,basis,opstr,indx,L,dtype,**blocks):
	a=blocks.get("a")
	kblock=blocks.get("kblock")

	dtype = _dtype(dtype)
	char = _type_conv[dtype.char]
	fortran_op = basis_ops.__dict__[char+"_t_op"]
	col,ME,error = fortran_op(N,basis,opstr,indx,L,kblock,a)

	if error != 0: raise FortranError(_basis_op_errors[error])

	return ME,col




def op_t_z(N,m,basis,opstr,indx,L,dtype,**blocks):
	a=blocks.get("a")
	kblock=blocks.get("kblock")
	zblock=blocks.get("zblock")

	dtype = _dtype(dtype)
	char = _type_conv[dtype.char]
	fortran_op = basis_ops.__dict__[char+"_t_z_op"]
	col,ME,error = fortran_op(N,m,basis,opstr,indx,L,zblock,kblock,a)

	if error != 0: raise FortranError(_basis_op_errors[error])

	return ME,col





def SpinOp(basis,opstr,indx,dtype):

	dtype = _dtype(dtype)
	char = _type_conv[dtype.char]
	fortran_op = basis_ops.__dict__[char+"_spinop"]
	col,ME,error = fortran_op(basis,opstr,indx)

	if error != 0: raise FortranError(_basis_op_errors[error])

	return ME,col


	
