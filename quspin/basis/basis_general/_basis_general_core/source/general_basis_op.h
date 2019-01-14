#ifndef _GENERAL_BASIS_OP_H
#define _GENERAL_BASIS_OP_H

#include <complex>
#include <limits>
#include "general_basis_core.h"
#include "numpy/ndarraytypes.h"
#include "misc.h"



template<class T>
int inline check_imag(std::complex<double> m,std::complex<T> *M){
	M[0].real(m.real());
	M[0].imag(m.imag());
	return 0;
}

template<class T>
int inline check_imag(std::complex<double> m,T *M){
	if(std::abs(m.imag())>1.1e-15){
		return 1;
	}
	else{
		M[0] = m.real();
		return 0;
	}
}



template<class I, class J, class K, class T>
int general_op(general_basis_core<I> *B,
						  const int n_op,
						  const char opstr[],
						  const int indx[],
						  const std::complex<double> A,
						  const npy_intp Ns,
						  const I basis[],
						  const J n[],
						  		K row[],
						  		K col[],
						  		T M[]
						  )
{
	const int nt = B->get_nt();
	int err = 0;
	int g[128],gg[128];
	#pragma omp parallel for schedule(static,1) private(g,gg)
	for(npy_intp i=0;i<Ns;i++){
		if(err != 0){
			continue;
		}

		I r = basis[i];
		std::complex<double> m = A;
		int local_err = B->op(r,m,n_op,opstr,indx);

		if(local_err == 0){
			int sign = 1;

			for(int k=0;k<nt;k++){
				gg[k]=g[k]=0;
			}

			K j = i;
			if(r != basis[i]){
				I rr = B->ref_state(r,g,gg,sign);
				j = binary_search(Ns,basis,rr);
			}

			if(j >= 0){
				for(int k=0;k<nt;k++){
					double q = (2.0*M_PI*B->qs[k]*g[k])/B->pers[k];
					m *= std::exp(std::complex<double>(0,-q));
				}
				m *= sign * std::sqrt(double(n[j])/double(n[i]));
				local_err = check_imag(m,&M[i]);
				col[i]=i;
				row[i]=j;
			}
			else{
				col[i] = i;
				row[i] = i;
				M[i] = std::numeric_limits<T>::quiet_NaN();
			}
		}

		if(local_err != 0){
			#pragma omp critical
			err = local_err;
		}
	}

	return err;
}



template<class I, class J, class K, class T>
int inline general_op_wrapper(void *B,
						  const int n_op,
						  const char opstr[],
						  const int indx[],
						  const std::complex<double> A,
						  const npy_intp Ns,
						  const void *basis,
						  const J n[],
						  		K row[],
						  		K col[],
						  		T M[]
						  )
{general_op(reinterpret_cast<general_basis_core<I> *>(B),n_op,opstr,indx,A,Ns,(const I*)basis,n,row,col,M);}



#endif
