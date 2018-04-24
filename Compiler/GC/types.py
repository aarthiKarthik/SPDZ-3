# (C) 2018 University of Bristol, Bar-Ilan University. See License.txt

from Compiler.types import MemValue, read_mem_value, regint, Array
from Compiler.program import Tape, Program
from Compiler.exceptions import *
from Compiler import util, oram, floatingpoint
import Compiler.GC.instructions as inst
import operator

class bits(Tape.Register):
    n = 40
    size = 1
    PreOp = staticmethod(floatingpoint.PreOpN)
    MemValue = staticmethod(lambda value: MemValue(value))
    @staticmethod
    def PreOR(l):
        return [1 - x for x in \
                floatingpoint.PreOpN(operator.mul, \
                                     [1 - x for x in l])]
    @classmethod
    def get_type(cls, length):
        if length is None:
            return cls
        elif length == 1:
            return cls.bit_type
        if length not in cls.types:
            class bitsn(cls):
                n = length
            cls.types[length] = bitsn
            bitsn.__name__ = cls.__name__ + str(length)
        return cls.types[length]
    @classmethod
    def conv(cls, other):
        if isinstance(other, cls):
            return other
        elif isinstance(other, MemValue):
            return cls.conv(other.read())
        else:
            res = cls()
            res.load_other(other)
            return res
    hard_conv = conv
    @classmethod
    def compose(cls, items, bit_length):
        return cls.bit_compose(sum([item.bit_decompose(bit_length) for item in items], []))
    @classmethod
    def bit_compose(cls, bits):
        if len(bits) == 1:
            return bits[0]
        bits = list(bits)
        res = cls.new(n=len(bits))
        cls.bitcom(res, *bits)
        res.decomposed = bits
        return res
    def bit_decompose(self, bit_length=None):
        n = bit_length or self.n
        if n > self.n:
            raise Exception('wanted %d bits, only got %d' % (n, self.n))
        if n == 1:
            return [self]
        if self.decomposed is None or len(self.decomposed) < n:
            res = [self.bit_type() for i in range(n)]
            self.bitdec(self, *res)
            self.decomposed = res
            return res
        else:
            return self.decomposed[:n]
    @classmethod
    def load_mem(cls, address, mem_type=None):
        res = cls()
        if mem_type == 'sd':
            return cls.load_dynamic_mem(address)
        else:
            cls.load_inst[util.is_constant(address)](res, address)
            return res
    def store_in_mem(self, address):
        self.store_inst[isinstance(address, (int, long))](self, address)
    def __init__(self, value=None, n=None):
        Tape.Register.__init__(self, self.reg_type, Program.prog.curr_tape)
        self.set_length(n or self.n)
        if value is not None:
            self.load_other(value)
        self.decomposed = None
    def set_length(self, n):
        if n > self.max_length:
            print self.max_length
            raise Exception('too long: %d' % n)
        self.n = n
    def load_other(self, other):
        if isinstance(other, (int, long)):
            self.set_length(self.n or util.int_len(other))
            self.load_int(other)
        elif isinstance(other, regint):
            self.conv_regint(self.n, self, other)
        elif isinstance(self, type(other)) or isinstance(other, type(self)):
            self.mov(self, other)
        else:
            raise CompilerError('cannot convert from %s to %s' % \
                                (type(other), type(self)))
    def __repr__(self):
        return '%s(%d/%d)' % \
            (super(bits, self).__repr__(), self.n, type(self).n)

class cbits(bits):
    max_length = 64
    reg_type = 'cb'
    is_clear = True
    load_inst = (None, inst.ldmc)
    store_inst = (None, inst.stmc)
    bitdec = inst.bitdecc
    conv_regint = staticmethod(lambda n, x, y: inst.convcint(x, y))
    types = {}
    def load_int(self, value):
        self.load_other(regint(value))
    def store_in_dynamic_mem(self, address):
        inst.stmsdci(self, cbits.conv(address))
    def clear_op(self, other, c_inst, ci_inst, op):
        if isinstance(other, cbits):
            res = cbits(n=max(self.n, other.n))
            c_inst(res, self, other)
            return res
        else:
            if util.is_constant(other):
                if other >= 2**31 or other < -2**31:
                    return op(self, cbits(other))
                res = cbits(n=max(self.n, len(bin(other)) - 2))
                ci_inst(res, self, other)
                return res
            else:
                return op(self, cbits(other))
    __add__ = lambda self, other: \
              self.clear_op(other, inst.addc, inst.addci, operator.add)
    __xor__ = lambda self, other: \
              self.clear_op(other, inst.xorc, inst.xorci, operator.xor)
    __radd__ = __add__
    __rxor__ = __xor__
    def __mul__(self, other):
        if isinstance(other, cbits):
            return NotImplemented
        else:
            try:
                res = cbits(n=min(self.max_length, self.n+util.int_len(other)))
                inst.mulci(res, self, other)
                return res
            except TypeError:
                return NotImplemented
    def __rshift__(self, other):
        res = cbits(n=self.n-other)
        inst.shrci(res, self, other)
        return res
    def print_reg(self, desc=''):
        inst.print_reg(self, desc)
    def print_reg_plain(self):
        inst.print_reg_plain(self)
    output = print_reg_plain
    def reveal(self):
        return self

class sbits(bits):
    max_length = 128
    reg_type = 'sb'
    is_clear = False
    clear_type = cbits
    default_type = cbits
    load_inst = (inst.ldmsi, inst.ldms)
    store_inst = (inst.stmsi, inst.stms)
    bitdec = inst.bitdecs
    bitcom = inst.bitcoms
    conv_regint = inst.convsint
    mov = inst.movs
    types = {}
    def __init__(self, *args, **kwargs):
        bits.__init__(self, *args, **kwargs)
    @staticmethod
    def new(value=None, n=None):
        if n == 1:
            return sbit(value)
        else:
            return sbits.get_type(n)(value)
    @staticmethod
    def get_random_bit():
        res = sbit()
        inst.bit(res)
        return res
    @classmethod
    def load_dynamic_mem(cls, address):
        res = cls()
        if isinstance(address, (long, int)):
            inst.ldmsd(res, address, cls.n)
        else:
            inst.ldmsdi(res, address, cls.n)
        return res
    def store_in_dynamic_mem(self, address):
        if isinstance(address, (long, int)):
            inst.stmsd(self, address)
        else:
            inst.stmsdi(self, cbits.conv(address))
    def load_int(self, value):
        if abs(value) < 2**31:
            if (abs(value) > (1 << self.n)):
                raise Exception('public value %d longer than %d bits' \
                                % (value, self.n))
            inst.ldbits(self, self.n, value)
        else:
            value %= 2**self.n
            if value >> 64 != 0:
                raise NotImplementedError('public value too large')
            self.load_other(regint(value))
    @read_mem_value
    def __add__(self, other):
        if isinstance(other, int):
            return self.xor_int(other)
        else:
            if not isinstance(other, sbits):
                other = sbits(other)
                n = self.n
            else:
                n = max(self.n, other.n)
            res = self.new(n=n)
            inst.xors(n, res, self, other)
            return res
    __radd__ = __add__
    __sub__ = __add__
    __xor__ = __add__
    __rxor__ = __add__
    @read_mem_value
    def __rsub__(self, other):
        if isinstance(other, cbits):
            return other + self
        else:
            return self.xor_int(other)
    @read_mem_value
    def __mul__(self, other):
        if isinstance(other, int):
            return self.mul_int(other)
        try:
            if min(self.n, other.n) != 1:
                raise NotImplementedError('high order multiplication')
            n = max(self.n, other.n)
            res = self.new(n=max(self.n, other.n))
            order = (self, other) if self.n != 1 else (other, self)
            inst.andrs(n, res, *order)
            return res
        except AttributeError:
            return NotImplemented
    @read_mem_value
    def __rmul__(self, other):
        if isinstance(other, cbits):
            return other * self
        else:
            return self.mul_int(other)
    def xor_int(self, other):
        if other == 0:
            return self
        self_bits = self.bit_decompose()
        other_bits = util.bit_decompose(other, max(self.n, util.int_len(other)))
        extra_bits = [self.new(b, n=1) for b in other_bits[self.n:]]
        return self.bit_compose([~x if y else x \
                                 for x,y in zip(self_bits, other_bits)] \
                                + extra_bits)
    def mul_int(self, other):
        if other == 0:
            return 0
        elif other == 1:
            return self
        elif self.n == 1:
            bits = util.bit_decompose(other, util.int_len(other))
            zero = sbit(0)
            mul_bits = [self if b else zero for b in bits]
            return self.bit_compose(mul_bits)
        else:
            print self.n, other
            return NotImplemented
    def __lshift__(self, i):
        return self.bit_compose([sbit(0)] * i + self.bit_decompose()[:self.max_length-i])
    def __invert__(self):
        # res = type(self)(n=self.n)
        # inst.nots(res, self)
        # return res
        one = self.new(value=1, n=1)
        bits = [one + bit for bit in self.bit_decompose()]
        return self.bit_compose(bits)
    def __neg__(self):
        return self
    def reveal(self):
        if self.n > self.clear_type.max_length:
            raise Exception('too long to reveal')
        res = self.clear_type(n=self.n)
        inst.reveal(self.n, res, self)
        return res
    def equal(self, other, n=None):
        bits = (~(self + other)).bit_decompose()
        return reduce(operator.mul, bits)

class bit(object):
    n = 1
    
class sbit(bit, sbits):
    def if_else(self, x, y):
        return self * (x ^ y) ^ y

class cbit(bit, cbits):
    pass

sbits.bit_type = sbit
cbits.bit_type = cbit

class bitsBlock(oram.Block):
    value_type = sbits
    def __init__(self, value, start, lengths, entries_per_block):
        oram.Block.__init__(self, value, lengths)
        length = sum(self.lengths)
        used_bits = entries_per_block * length
        self.value_bits = self.value.bit_decompose(used_bits)
        start_length = util.log2(entries_per_block)
        self.start_bits = util.bit_decompose(start, start_length)
        self.start_demux = oram.demux_list(self.start_bits)
        self.entries = [sbits.bit_compose(self.value_bits[i*length:][:length]) \
                        for i in range(entries_per_block)]
        self.mul_entries = map(operator.mul, self.start_demux, self.entries)
        self.bits = sum(self.mul_entries).bit_decompose()
        self.mul_value = sbits.compose(self.mul_entries, sum(self.lengths))
        self.anti_value = self.mul_value + self.value
    def set_slice(self, value):
        value = sbits.compose(util.tuplify(value), sum(self.lengths))
        for i,b in enumerate(self.start_bits):
            value = b.if_else(value << (2**i * sum(self.lengths)), value)
        self.value = value + self.anti_value
        return self

oram.block_types[sbits] = bitsBlock

class dyn_sbits(sbits):
    pass

class DynamicArray(Array):
    def __init__(self, *args):
        Array.__init__(self, *args)
    def _malloc(self):
        return Program.prog.malloc(self.length, 'sd', self.value_type)
    def _load(self, address):
        return self.value_type.load_dynamic_mem(cbits.conv(address))
    def _store(self, value, address):
        if isinstance(value, MemValue):
            value = value.read()
        if isinstance(value, sbits):
            self.value_type.conv(value).store_in_dynamic_mem(address)
        else:
            cbits.conv(value).store_in_dynamic_mem(address)

sbits.dynamic_array = DynamicArray
cbits.dynamic_array = Array
