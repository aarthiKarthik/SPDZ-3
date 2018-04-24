// (C) 2018 University of Bristol, Bar-Ilan University. See License.txt

/*
 * Secret.cpp
 *
 */

#include <GC/FakeSecret.h>

namespace GC
{

int FakeSecret::default_length = 128;

ostream& FakeSecret::out = cout;

void FakeSecret::load(int n, const Integer& x)
{
	if ((size_t)n < 8 * sizeof(x) and abs(x.get()) >= (1LL << n))
		throw out_of_range("public value too long");
	*this = x;
}

void FakeSecret::bitcom(Memory<FakeSecret>& S, const vector<int>& regs)
{
    *this = 0;
    for (unsigned int i = 0; i < regs.size(); i++)
        *this ^= (S[regs[i]] << i);
}

void FakeSecret::bitdec(Memory<FakeSecret>& S, const vector<int>& regs) const
{
    for (unsigned int i = 0; i < regs.size(); i++)
        S[regs[i]] = (*this >> i) & 1;
}

void FakeSecret::load(vector<ReadAccess<FakeSecret> >& accesses,
        const Memory<FakeSecret>& mem)
{
    for (auto access : accesses)
        access.dest = mem[access.address];
}

void FakeSecret::store(Memory<FakeSecret>& mem,
        vector<WriteAccess<FakeSecret> >& accesses)
{
    for (auto access : accesses)
        mem[access.address] = access.source;
}

void FakeSecret::store_clear_in_dynamic(Memory<DynamicType>& mem,
		const vector<GC::ClearWriteAccess>& accesses)
{
	for (auto access : accesses)
		mem[access.address] = access.value;
}

} /* namespace GC */
