// (C) 2018 University of Bristol, Bar-Ilan University. See License.txt

/*
 * Secret.h
 *
 */

#ifndef GC_FAKESECRET_H_
#define GC_FAKESECRET_H_

#include "GC/Clear.h"
#include "GC/Memory.h"
#include "GC/Access.h"

#include "Math/Share.h"
#include "Math/gf2n.h"

#include <random>

namespace GC
{

class FakeSecret : int128
{
    __uint128_t a;

public:
    typedef FakeSecret DynamicType;

    static string type_string() { return "fake secret"; }
    static string phase_name() { return "Faking"; }

    static int default_length;

    typedef ostream& out_type;
    static ostream& out;

    static void store_clear_in_dynamic(Memory<DynamicType>& mem,
    		const vector<GC::ClearWriteAccess>& accesses);

    static void load(vector< ReadAccess<FakeSecret> >& accesses, const Memory<FakeSecret>& mem);
    static void store(Memory<FakeSecret>& mem, vector< WriteAccess<FakeSecret> >& accesses);

    template <class T>
    static void andrs(T& processor, const vector<int>& args)
    { processor.andrs(args); }

    FakeSecret() : a(0) {}
    FakeSecret(const Integer& x) : a(x.get()) {}
    FakeSecret(__uint128_t x) : a(x) {}

    __uint128_t operator>>(const FakeSecret& other) const { return a >> other.a; }
    __uint128_t operator<<(const FakeSecret& other) const { return a << other.a; }

    __uint128_t operator^=(const FakeSecret& other) { return a ^= other.a; }

    void load(int n, const Integer& x);
    template <class T>
    void load(int n, const Memory<T>& mem, size_t address) { load(n, mem[address]); }
    template <class T>
    void store(Memory<T>& mem, size_t address) { mem[address] = *this; }

    void bitcom(Memory<FakeSecret>& S, const vector<int>& regs);
    void bitdec(Memory<FakeSecret>& S, const vector<int>& regs) const;

    template <class T>
    void xor_(int n, const FakeSecret& x, const T& y) { (void)n; a = x.a ^ y.a; }
    void andrs(int n, const FakeSecret& x, const FakeSecret& y) { (void)n; a = x.a * y.a; }

    void random_bit() { a = random() % 2; }

    void reveal(Clear& x) { x = a; }
};

} /* namespace GC */

#endif /* GC_FAKESECRET_H_ */
