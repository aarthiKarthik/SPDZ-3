// (C) 2018 University of Bristol, Bar-Ilan University. See License.txt

/*
 * Instruction.cpp
 *
 */

#include <algorithm>

#include "GC/Instruction.h"
#ifdef MAX_INLINE
#include "GC/Secret_inline.h"
#endif
#include "Processor/Instruction.h"
#include "BMR/Party.h"

#include "Secret.h"
#include "Tools/parse.h"

#include "GC/Instruction_inline.h"

namespace GC
{

#define X(NAME, CODE) template<class T> bool NAME##_code(const Instruction<T>& instruction, \
        Processor<T>& processor) { (void)instruction; (void)processor; CODE; return true; }
    INSTRUCTIONS
#undef X

template <class T>
Instruction<T>::Instruction() :
        BaseInstruction()
{
    code = fallback_code;
    size = 1;
}

template <class T>
bool Instruction<T>::get_offline_data_usage(int& usage)
{
    switch (opcode)
    {
    case ::USE:
        usage += n;
        return int(n) >= 0;
    default:
        return true;
    }
}

template <class T>
int Instruction<T>::get_reg_type() const
{
    switch (opcode & 0x2F0)
    {
    case SECRET_WRITE:
        return SBIT;
    case CLEAR_WRITE:
        return CBIT;
    default:
        switch (::BaseInstruction::get_reg_type())
        {
        case ::INT:
            return INT;
        case ::MODP:
            switch (opcode)
            {
            case LDMC:
                return CBIT;
            }
            return SBIT;
        }
        return NONE;
    }
}

template<class T>
int GC::Instruction<T>::get_max_reg(int reg_type) const
{
    int skip;
    switch (opcode)
    {
    case LDMSD:
    case LDMSDI:
        skip = 3;
        break;
    case STMSD:
    case STMSDI:
        skip = 2;
        break;
    default:
        return BaseInstruction::get_max_reg(reg_type);
    }

    int m = 0;
    if (reg_type == SBIT)
        for (size_t i = 0; i < start.size(); i += skip)
            m = max(m, start[i] + 1);
    return m;
}

template <class T>
int Instruction<T>::get_mem(RegType reg_type) const
{
    int m = n + 1;
    switch (opcode)
    {
    case LDMSD:
        if (reg_type == DYN_SBIT)
        {
            m = 0;
            for (size_t i = 0; i < start.size() / 3; i++)
                m = max(m, start[3*i+1] + 1);
            return m;
        }
        break;
    case STMSD:
        if (reg_type == DYN_SBIT)
        {
            m = 0;
            for (size_t i = 0; i < start.size() / 2; i++)
                m = max(m, start[2*i+1] + 1);
            return m;
        }
        break;
    case LDMS:
    case STMS:
        if (reg_type == SBIT)
            return m;
        break;
    case LDMC:
    case STMC:
        if (reg_type == CBIT)
            return m;
        break;
    case LDMINT:
    case STMINT:
        if (reg_type == INT)
            return m;
        break;
    }
    return 0;
}

template <class T>
void Instruction<T>::parse(istream& s, int pos)
{
    n = 0;
    start.resize(0);
    ::memset(r, 0, sizeof(r));

    int file_pos = s.tellg();
    opcode = ::get_int(s);

    try {
        parse_operands(s, pos);
    }
    catch (Invalid_Instruction& e)
    {
        int m;
        switch (opcode)
        {
        case XORM:
            n = get_int(s);
            get_ints(r, s, 3);
            break;
        case XORCI:
        case MULCI:
        case LDBITS:
            get_ints(r, s, 2);
            n = get_int(s);
            break;
        case BITDECS:
        case BITCOMS:
        case BITDECC:
            m = get_int(s) - 1;
            get_ints(r, s, 1);
            get_vector(m, start, s);
            break;
        case CONVCINT:
            get_ints(r, s, 2);
            break;
        case REVEAL:
        case CONVSINT:
            n = get_int(s);
            get_ints(r, s, 2);
            break;
        case LDMSDI:
        case STMSDI:
        case LDMSD:
        case STMSD:
        case STMSDCI:
        case XORS:
        case ANDRS:
            get_vector(get_int(s), start, s);
            break;
        default:
            ostringstream os;
            os << "Invalid instruction " << showbase << hex  << opcode
                    << " at " << dec << pos << "/" << hex << file_pos << dec;
            throw Invalid_Instruction(os.str());
        }
    }

    switch(opcode)
    {
#define X(NAME, CODE) case NAME: \
      code = NAME##_code; \
      break;
    INSTRUCTIONS
#undef X
    default:
        ostringstream os;
        os << "Code not defined for instruction " << showbase << hex << opcode << dec;
        throw Invalid_Instruction(os.str());
        break;
    }
}



template class Instruction<FakeSecret>;
template class Instruction< Secret<PRFRegister> >;
template class Instruction< Secret<EvalRegister> >;
template class Instruction< Secret<GarbleRegister> >;
template class Instruction< Secret<RandomRegister> >;

} /* namespace GC */
