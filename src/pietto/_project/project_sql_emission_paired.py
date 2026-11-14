"""Phase77 Wave A paired forms, names aside.

MySQL opens a Wave A construct only in a statement that is byte for byte one
form the slice's qualification pack runs on both PostgreSQL and MySQL, with
only its names changed, under the literal policy the pack runs it with. Each
reader reduces its own input to those bytes without names and compares their
digest with the form's: emission and the live verifier the selected module and
the request's contract, compiled replay the bundle's records. A name is an
ASCII identifier of at most 63 bytes that does not start with `__pietto`, and
two names of a kind are equal ignoring case exactly where the form's names in
their places are; a table locator has exactly two such parts. In a module, a
word that is one of its slice's keywords is that keyword, never a name; a
bundle's records hold each name in a field of its own, so there a name is
read by its place, whatever word it is. A paired statement whose emission
does not give its form's SQL, names aside, reports main's output, derived
again as main (rows.AS_MAIN, which `closed` sets); so do loading and compiled
emission for a bundle whose records are a form but that another check
refuses, or whose SQL is not the form's. Records a reader cannot read,
checked yet or not, are no form.
"""

from contextlib import contextmanager
import hashlib
import json
import re

from pietto._project import project_compiled_schema as schema
from pietto._project import project_sql_emission_rows as rows
from pietto._project.project_sql_plan_literals import ProjectSQLLiteralPolicy

__all__: tuple[str, ...] = ()

# S16 lag/lead Text defaults: P-S16-1 s16_text_defaults, P-S16-2
# s16_quote_default, P-S16-3 s16_x_metadata. S10 conditional counts and tests
# of a group, one form per body: P-S10-1 and 5 s10_grouped and
# s10_empty_grouped, P-S10-2 s10_keyed, P-S10-3 and 4 s10_ungrouped and
# s10_empty_ungrouped. S08 count, min and max windows: P-S08-1..7
# s08_count_star, s08_min_rows_frame, s08_min_partition,
# s08_count_named_window, s08_grouped_window, s08_qualify_count,
# s08_join_window, then P-S08T-1..4 s08_temporal_candidate,
# s08_temporal_nullable, s08_temporal_partition, s08_temporal_peers. S11
# distinct-tuple counts, one form per body: P-S11-1 to 8 s11_join_left,
# s11_join_left_alias, s11_join_inner, s11_join_inner_alias,
# s11_join_text_bykey, s11_join_text_bykey_inner, s11_join_global and
# s11_join_collapse, P-S11B-1 and 4 s11_tuples and s11_empty, P-S11B-2
# s11_int_pair, P-S11B-3 s11_grouped. S14 conditionals beside a JOIN and
# scalar calls in aggregate arguments over JOIN rows: P-S14-1 to 4
# s14_e2_joined_pred, s14_e2_from_pred, s14_e3_aggregate_calls and
# s14_e2e3_bind_safe, the last with bind-safe literals. S17 Decimal and Int
# arithmetic and signs: the bodies of P-DEC-1 to 3, 4 to 6, 7 to 9 and 10 to
# 12 (dec_param_add, rsub, mul and rmul, each run with three arguments), then
# P-DECB-1 to 10 dec_int_add_sub, dec_int_left_add_sub, dec_times_int,
# dec_int_times, dec_times_literal, dec_neg, dec_pos, dec_neg_product,
# dec_different_scale and dec_65_30_product. Each form holds one slice's
# construct only, so a form opens no other slice. Per form: the sha256 of the
# module and contract, of the emitted SQL and of the compiled records, and the
# number of compiled records.
FORMS = (
    (
        "9e74ea22bb430348248b9b5dc0ef1c38f4c829020dd6015cd6e4703d0efb71a2",
        "04387d1f0036bec34c49dbf283841b3740c5acc9783987459b15fd2566f125a7",
        "ece6d96ec01710452e751bded39da4c75aca195793fa056a2e6817c74130fd74",
        324,
    ),
    (
        "432e21a98ca1d781df1810c46e769404fd94a1fd1aa99ae7bc8c88490669da83",
        "bdc484a6bde767f263ac84291765a56cf9926a1a849a742cfa3b46188d674eaa",
        "0c8242877a91b2be7b0fbfb4cc855ea505983c675719e6c2619756ce8f60b7d7",
        273,
    ),
    (
        "40ed6ecb83301498a5a7e5ea21ec9a44d51c53bfa14d53faefd645ead2ca68c6",
        "72a29d6b8bc61f2bd0258601037240310c6a7f0e20029a8822b6d9ca4acb57cf",
        "2a865393b1dac80e5bef3254dfe253d540521f32b2ce28ee200595d3bd0ebb9f",
        400,
    ),
    (
        "7f14a6a0bad8ddfd6644de455f43a9ee40c7a2f8fd2cc5c132bcb8285a276a97",
        "ceb4cc6bcfc77a5817464db9be6b273916e49a8f78c29d93569aad264d8349fb",
        "4e52280d2a85a572168201774ea7eed294e3a812e278a3711a75b67108c1287d",
        244,
    ),
    (
        "811486a36f578a810489f1df7ee086afabce5701d5fe8446bccbeee94bda285c",
        "d5628848ca30cc9d84ae8f49d7ac0363c898502fce64a2f532f87eb9f07ade7e",
        "5c8465ac3d7bb9eec20999a74d8d223ff672b0f7c85cbbef4835515b6274e247",
        261,
    ),
    (
        "436e0b08564b3324fb70e675474a9fce514452549f5e7f9f0611eda51490ea34",
        "05e5c80a7b86df2a99f1b894004b813653e0ef4c4963a038860b4ff3a67823ae",
        "b80218928139e48c915505367a036dcd878a990b6601eb1b9c0315eb5e89ae62",
        231,
    ),
    (
        "de3911508cfe1d23303aa7e861e3363f3cdf44d69c011eb6435caf1ee2883daf",
        "20bf9012ca0cae87d5708529d4007bcc060a8554d56f77c21d52759aadf71e5d",
        "101a7c578cb380ecaf06648523cc2f30e5c0be3d7071e5981634679e2db4f4ab",
        200,
    ),
    (
        "5adfa74a35a6dd0ec935c99ec81415a52c33e25f6c3577c0b7feec7cd3c67524",
        "d0f2bbf5b730b9f70eb80ae780a756bc1f602d30f3ed6d574f892a3be3927a86",
        "215da21f96f9346560072783a72acfa6dcdbfe9462162b36d149e92bd6ec141f",
        207,
    ),
    (
        "a79412e1f82795e327940e49a3dc3060aa87ffe0fecb41e21145e40cc1025494",
        "5e2086cb34cbc57578302c4909f1006612dee675aada25613f01bca086a32bde",
        "8f06627b7ffe33783597e907aec10cead021997d047c7052a232ec505527442a",
        208,
    ),
    (
        "cdd8cffc59776430ff0af07d1a9f9900924e7ef3585bd9a7c83896bc86cfd4a4",
        "7a7d9b6ddbf9bb8d0db9bb9ee81ed48f490a0bf3c1e1665343fd675149b464ae",
        "8bfc2193ad925bedc5eb4208405b1e3e5a028e325effba460a77fc22573a30eb",
        189,
    ),
    (
        "c8cff8bd5d5e451001493d8c28fb84162ef8e9f8bf7a27eff53079059cad8bde",
        "142d52ad17d5b6baf2a44a8b0d32f49526cdb153d87dc36cd6c18f82ebb9fc83",
        "de86612652c05e457ec911c20ad7fe91a40be91515e04f36cb874f9b0041f2f4",
        269,
    ),
    (
        "2450c149e7e9958e1d812d099f1b8d4ed07013f0af4eda5272394f5b03c26d8d",
        "1b4b8f9d3a0c37992c9137f1a5df87c924320e6815b5d87c2b45f2819fee0444",
        "841064d42d1424736f00640ab21ddf33cf453fbb7a91221ad9bed194b6329d94",
        272,
    ),
    (
        "a0852ecfce5d589a31c0301db57d2c44a3b7ff3c5a01e2dd606797b656618ba6",
        "bea589009b5b55b492b54397f7e5567f36ee3980edb2566f61e96ee7541df254",
        "4fdb3952bc52b824485085e7a2f78f31ae18bd48e8fb6d6121fcaa140335de5d",
        431,
    ),
    (
        "6f5d496f6380c0c71e81d7a65160fa17900f311b23b57a87761a4bf86940f0b4",
        "027502870da4e06e56aef5ca37b1577cf1f776dc60ca701b80db95e2686ce33b",
        "d4f0b198b0b2ddb72b744d8ef2fe2ab316dc0be77eae8cc61e3b337fb844a17a",
        418,
    ),
    (
        "44c054b3cd6bf99fb7ce49e2d378b4227b915e678fbc92bbecb03e20b45dc37d",
        "18b4efe0b94c4c2402877a1771a923114fc0a780e27cb88a6715f5a04ba15148",
        "ece468bbccbc6cabef3203e3474b4b0523014368b8714ce544848346d28e1a6e",
        482,
    ),
    (
        "83dfc6a6161a7903a96c1a0a621f26e1a6f4bcbced44636505434a28c7d0949b",
        "11d908f358e6ceea85dc7395edc019f54b9eaf74ccce6e9c188c5e411c5784b0",
        "0995a3c402c6c3cee26fb948b4ad89d851afb4c7464ded238cdb9cfd301313c3",
        451,
    ),
    (
        "d7124d90bbd7589a188bace72c7d93f0f5359dc37ed2807dab67e8d911084d06",
        "97079b6933f625e435c748773e941127c6b36deaa338ec53354537813c4ac969",
        "5c4960a8164bc48aa2ebaee92d4ed399762bbe5de224da5fb63813bdb0842170",
        478,
    ),
    (
        "f3998966a5c533d434db82ad99ca2658298bdcba8aaad3a8e05ffb8970f24d53",
        "b6e6ff2489fc67d757bfb8c0db3705778879c45f5171a75b15ab0c237dd6c961",
        "7c8ef0ed9b4c7700041683da5cd8cf705cc3f8e72a9b51e85c0de1c336eadece",
        630,
    ),
    (
        "6ddcc037e00caa987c24b8911a692e71c152406b72b6a1f044fad14de7f9c375",
        "1e9abf6802ef81d9b456097a6355eb58453c3d872f7dae5af0d372f39f88ab79",
        "b8091546fdc91bedc8e14e30378e2f3339e533a9a1674c30b057a3bdfc7e95e5",
        630,
    ),
    (
        "e143808797cac85ea5f59f64bba6a7fa32c7c4d5300a7f9879873c6e68326ba4",
        "8afdaf6c550937a2740756232e0f70eefee334620339015dc57b322f43f743b6",
        "c06cc387e7db44f97760a68e3935a2f407eac0851fa7986ba49a40138687081c",
        630,
    ),
    (
        "e3d129fedb662a191f2aa827177ba5a3ec3324044ca80f5cdee6cc34ae79298d",
        "2076eebf2d4ef87a861381517aea593de1939bd578788114e23c98654b99586a",
        "3c8c666974b1b9884bf36c3a61c07722f66450488811b8b38fc069b6e9e65ac5",
        630,
    ),
    (
        "9d88ef39a7e6ced91d5174307f1829dd491849075d55244ed6bcb7d8157e51b0",
        "1b7fa4c3ca2f63217b81cb3b925c552692cab8da5dc35cb9d32df93877ee7c42",
        "7a6e896ecf22bdca8f51a0016a1b7de624b6f3b00a64752b90189c12092c6d61",
        625,
    ),
    (
        "be64c446d6c1b8e8723fb5bbab1de34eb7107eb4edbcfe6cc6331fe0b4faeef0",
        "3a8a8849732fa9426245c3f9296893371708e8722180f526e8287d1bec57fb52",
        "92497eaf98acb60d8b2a8f59f3602232aa14a624a92a1296a9f835af803c7ad8",
        625,
    ),
    (
        "b36bffb9f459e223e3da4c7ec4d906bd2f209f0a5cb551df5713ead38b610460",
        "c4e9f5255664cb2a9e14ec03d36d69f23902445a483a470821b30e09c9d769fa",
        "99fe4c5b964adaa0fc637fe52dd9821a9ba1ccf5c0798782897e8a1aafa926e6",
        592,
    ),
    (
        "7b8506dcf09da96656f43a16e7ba046f7ebb5dcd9c169bd623806bba85f9c8e0",
        "51a40a473376ccd45b7812019ff5e4b1e6bb013dab00a401f616dbfd3b64c1d6",
        "4db0b7a403a9f10006c3a801ea7c0e9d59a5829178c218041a0898ee3aa86285",
        671,
    ),
    (
        "9e7d1fb88b9e65b948ea35255b45434d97507c3c5d82af0c55bc5dcb0914cb82",
        "e92aa118987797dd593e56eaa6abefc404abf922c0d72f68b21fd46c8b1aabdf",
        "274cf13859783451bea8f887a4a6475d41e86ca91e29f391debbe51126df9cdd",
        239,
    ),
    (
        "370e882c81a854a31964bb370c3d9a8f8a8bd28d98351113d7a65ce0b411fd72",
        "a22efc077fc1dfc4bc1d81bdb674d892a0d69b5371be730ea6024a4f5aa004cc",
        "8df5726de8c7c52e618bed46a4ad62b2d1b59c89f2226c466769c833229dd1d9",
        154,
    ),
    (
        "32c7063dfc261f7a25026d0a83a70b18a47a15337eb9ffc3601de17617823b01",
        "d74f6ba0b14b04a10b9ab352e43464f9b5396faa5b68778b3846fd5f3f4b7086",
        "ef3974b8d111ff425d048e8553be1497d626fc52f6677dd25c3862ec8847ee11",
        184,
    ),
    (
        "6e43ebcc66430199692e91fa47626d136a892e9d481ef216b86bf76a1c436fa7",
        "8eebe70498ba3932c8a2a9060c62d0222f8f7fb94e83ea571e3a47a4438c66da",
        "f7a95c1f54dc670055255e1c7e4f1e4a7eec7741274d744362505802fd33eacd",
        372,
    ),
    (
        "e85faf2ccfc2686eeb8ea2ce100a088df99d112e5438f742e94f3bd81b473ac2",
        "4de1e6acd6d0f00d68c64aa8aa5037f6a746d1bec013a18933768bfb6e914274",
        "71008d02aaa1a763bf12874600e89f07218c6d65991b6cc02814e4cf529d1a31",
        372,
    ),
    (
        "543f18dfe3438701e53cda050739dc62d7777d0669ad6e37ff8708283ea1c6e1",
        "58583d9d3e705bd09299c0d752586af5af05ba0d20e523e4c5d6372d78b7ad3b",
        "46a278ed9c417b1eca38cfd9eb3dd0544885d81d43b9d8f2ad81ea715ff5f63f",
        437,
    ),
    (
        "8260af7bb423fe7e41cfd2ec7cf4c1fc858245b18873851c396172805a71dec5",
        "a9197853110bed0c152a03f7af47a90de532aac1666b9e6861f459ed619e649d",
        "a66c32d9ddd99645754c4fc57dfc7e9af968e48d161d9bf445d1987461f7dfed",
        459,
    ),
    (
        "40caa1266a743e2166d5e465c814b9e1a285b43f51af8209215aa8dd5e0e8235",
        "635ecfed70203720d8c72120d91f9e6b8eb10edf4ec86db43e0a8e5fd596a4ce",
        "4c1b533af76d474f1a5ac2b18837e5446e022083f33a8ba6c0f6f72e71d3a8e2",
        117,
    ),
    (
        "dd72417b56ca73af70976f74e9926c94b0401777c43a8ff331c097078156c4de",
        "b93d96a4e3af14008a33f6aa991193ac4ac3d35e0e8ad7aee975efc23917ff55",
        "c1c250e4054a6133795c8a6bc7b9a22f3d228433c03eaa387784f3e6e97029bc",
        117,
    ),
    (
        "579d8056f7ec143916478971f98fa1e5e9c6e36cc52068da7092d8ed8f42c1b1",
        "9cd78230f2251c8fcf79ca9a04f62c138d7aa6f531d6d1c852d1dd6b99ab0ba9",
        "07c541e3d347657cb9d18afca6a59083b4d8134a2f18a4c3c0055c236243c5bb",
        117,
    ),
    (
        "23ce96aab770f86ce902246df54a059549278c0a5b3d11fbd7cafdda50e389d0",
        "19e4d10075ac7bbd6174f84d7fb8d93c4ef72051f59d7e43006c167166e6c5c1",
        "9eaee2c133f7f2cacdf0e31c020aea8f456d3f55f8ee47b00ae30ccd22e38c06",
        117,
    ),
    (
        "f7038e7f1df3dd0cecb790ddab82201a6f5c8c75f0024b57c8f0dcd348e1ab9f",
        "30dd692a4b854caab4dce7dc271abf30383e6fc7a4b055ca23deef1f76cbfd55",
        "d76f7daeb94d9731a781720ce31293ac64cce75b65d73d98acdf089e9fa6e8e3",
        143,
    ),
    (
        "4da70bfc7f35f473807a539183766f4534e936fdbd759e71a645b5c567f91415",
        "30dd692a4b854caab4dce7dc271abf30383e6fc7a4b055ca23deef1f76cbfd55",
        "e25b79a6d443fbad47cce5e226d9e1d1a18745c713a7a924b26148e5f1b99f30",
        143,
    ),
    (
        "8390f4777f5452d51c383ba1837dff381258719d9752c6dd81eccf8af658ba31",
        "252f666e6107df6ede389eaa68a64de8312a20dd522411a068094a1bf0c09a9a",
        "08c1f1eba0d7676dc2decbccdb2bb52391163b9da7174083e53ad6edfd924ce9",
        114,
    ),
    (
        "0912b7609fc4355bbcddd38e2de4bbfc61113c30d342130a1554f4dfb2e58ed1",
        "252f666e6107df6ede389eaa68a64de8312a20dd522411a068094a1bf0c09a9a",
        "85b92a0f414c0c10ae4e6c1e6a2ea3cda56833cfa8f59351c9144da1ab19193b",
        114,
    ),
    (
        "23c7862c63c2e694d337e2d1c76ea45411598636295bd303bcec494396cff17d",
        "28ad5a297191a8169e421e731e8a043333fd0b59446ea619a1f0ef0e1aca1b15",
        "f8224592f0a543449ee50bbff134685ad4b931dd0e19c03def959d8fb1a5b7ec",
        116,
    ),
    (
        "32c4a9183f17dbfadb7a3a9757d4aedfeb6a38c5718c3588e03bd4733ff386d1",
        "7937bcc9dce925e64edaad9549a3feb27aa0573cb15667f003c2d55bec7d21a0",
        "6f423f9af60f056a6fee9fa43e747a174562c61349e07eec70649446537e9e43",
        109,
    ),
    (
        "ca89406b07efe4d0ec0af577a2fa622b55ba6031e66069ea9f9d252d323b2d40",
        "1206701156d08579ec57c4c761c27565832dceb52c29835a725154f9ff011adf",
        "79192e9e3a9252634d8b4f647bf50f1292496d4210152a3f30f6dbf293b75974",
        109,
    ),
    (
        "81446c3a1667dfc78a5d174195a12d7aa4cfb161ee835c8a0441ba1ea6488703",
        "da93d68cf6329024336d679189e97d2baa9d419c7a072c9e8e91e4279d94487d",
        "8d280ca7c9d7d6e269feca8a074cd70692ff6512a642fb44bd601021341a43a4",
        119,
    ),
    (
        "8e4f5b3b5785d988e7f7dde8e2613f4339d26cf4eef2c25d853bf1b8c791c963",
        "30dd692a4b854caab4dce7dc271abf30383e6fc7a4b055ca23deef1f76cbfd55",
        "7bee64d8ac28d5a2554052992157cfe9a09a24d4061ddd01c73476460303d803",
        149,
    ),
    (
        "97645bb9440b43f361b53030cbdcaf96d818eeae6db6b3083e332ddbef11c8c9",
        "252f666e6107df6ede389eaa68a64de8312a20dd522411a068094a1bf0c09a9a",
        "cd6d8a077228289c9e1cc9747f756c7c5227b7ea62b6bbcd759294661e944ff5",
        114,
    ),
)
_S16_FIXED = frozenset(
    "shape source query from select window order by lag lead mysql table"
    " Int Bool Text Decimal Float None".split()
)
# Per slice: its forms and its keywords, the words of its forms that are no
# names there (S08's: S16's and its own); another slice's keywords stay names.
SLICES = (
    (range(3), _S16_FIXED),
    (
        range(3, 6),
        frozenset(
            "shape source query from select group by sum for in if all any unique"
            " mysql table Int Bool Text Decimal Float None".split()
        ),
    ),
    (
        range(6, 17),
        _S16_FIXED
        | frozenset(
            "count min max partition between preceding and current row let group"
            " qualify inner join on Timestamp Date UUID".split()
        ),
    ),
    (
        range(17, 28),
        frozenset(
            "shape source query table from let left inner join on group by select"
            " count_distinct unique mysql Int Bool Text Decimal Float None".split()
        ),
    ),
    (
        range(28, 32),
        frozenset(
            "shape source query from where let left inner join on group by select"
            " count count_distinct lower trim len def return if else unique mysql"
            " table Int Text None".split()
        ),
    ),
    (
        range(32, 46),
        frozenset(
            "shape source query table from select mysql Int Bool Text Decimal Float"
            " None".split()
        ),
    ),
)
# re.ASCII: IGNORECASE alone lets the Kelvin sign match k (D77.36 ASCII names).
_NAME = re.compile(r"(?!__pietto)[A-Za-z_][A-Za-z0-9_]{0,62}", re.ASCII | re.IGNORECASE)
# The frame keyword `rows` (group 2) is no name, unlike the forms' source `rows`;
# no S16 or S10 form has a frame, so no such statement with one pairs either way.
_TOKEN = re.compile(
    r'(?<=mysql\.table\()"([^"\\\n]*)"|"(?:[^"\\\n]|\\.)*"|(rows)(?= between )|[^\W\d]\w*'
)
_QUOTED = re.compile(r"`(?:[^`]|``)*`")
_COMPILED_NAMES = {
    "source": (("namespace", "S"), ("name", "R")),
    "field": (("label", "N"), ("column", "C")),
    "declaration": (("module", "M"), ("label", "N")),
    "output": (("label", "N"),),
    "port": (("label", "N"),),
    "parameter": (("label", "N"),),
}


@contextmanager
def closed():
    """Read every statement as main does (rows.AS_MAIN): unpaired."""
    token = rows.AS_MAIN.set(True)
    try:
        yield
    finally:
        rows.AS_MAIN.reset(token)


class _Names:
    """Names by kind in order of first use; `valid` once every one is a name.
    A name equal ignoring case to an earlier one of its kind also names that
    one, so a renaming keeps which names MySQL may fold together."""

    def __init__(self):
        self.seen, self.folded, self.valid = {}, {}, True

    def __call__(self, kind, name):
        if type(name) is not str:
            raise TypeError("name")
        if (kind, name) not in self.seen:
            parts = name[:-7].split(".") if kind == "M" else name.split(".")
            self.valid &= (
                (name.endswith(".pietto") if kind == "M" else True)
                and len(parts) == (2 if kind == "L" else 1)
                and all(_NAME.fullmatch(part) for part in parts)
            )
            count = sum(seen[0] == kind for seen in self.seen)
            first = self.folded.setdefault((kind, name.lower()), count)
            twin = "" if first == count else f"~{first}"
            self.seen[kind, name] = f"\0{kind}{count}{twin}\0"
        return self.seen[kind, name]


def _module(text, names, fixed):
    def token(match):
        if match[1] is not None:
            return '"' + names("L", match[1]) + '"'
        if match[2] is not None or match[0][0] == '"' or match[0] in fixed:
            return match[0]
        return names("N", match[0])

    lines = "".join(line + "\n" for line in text.split("\n") if line)
    return _TOKEN.sub(token, lines)


def _contract(raw, names):
    document = json.loads(raw)
    for source in document["sources"]:
        selector, relation = source["selector"], source["relation"]
        selector["module"] = names("M", selector["module"])
        selector["name"] = names("N", selector["name"])
        relation["namespace"] = names("S", relation["namespace"])
        relation["name"] = names("R", relation["name"])
        for field in source["fields"]:
            field["name"] = names("N", field["name"])
            field["column"] = names("C", field["column"])
    return json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _form(column, text, names, forms=range(len(FORMS))):
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    for index in forms:
        if FORMS[index][column] == digest:
            return index if names.valid else None
    return None


def project_text(path, source, contract, selected, names, fixed):
    """One module's bytes, its contract and its selected (name, kind), with
    the literal policy when it is not preserve, names and `fixed`, one
    slice's keywords, aside."""
    return "\0".join(
        (
            names("M", path),
            _module(source, names, fixed),
            _contract(contract, names),
            names("N", selected[0]),
            *selected[1:],
        )
    )


def project_form(request):
    """The paired form the selected statement of this project request is, or None."""
    if rows.AS_MAIN.get() or request.family != "mysql":
        return None
    try:
        checked = request.verification
        result = checked.completed.semantic_result
        owner = checked.selected_owner.identity
        (snapshot,) = result.trusted_source_snapshots
        selected = (owner.declared_name, owner.declaration_kind.value)
        if checked.literal_policy is not ProjectSQLLiteralPolicy.PRESERVE_LITERALS:
            selected += (checked.literal_policy.value,)
        if (
            len(result.modules) != 1
            or owner.module_path != snapshot.path
            # Every paired module is far shorter; this bounds each call's work.
            or len(snapshot.source_text) > 8192
        ):
            return None
        for forms, fixed in SLICES:
            names = _Names()
            text = project_text(
                snapshot.path,
                snapshot.source_text,
                request.accepted_bytes,
                selected,
                names,
                fixed,
            )
            form = _form(0, text, names, forms)
            if form is not None:
                return form
    except (ValueError, TypeError, LookupError, AttributeError, RecursionError):
        return None
    return None


def sql_text(sql):
    """Emitted SQL with each quoted name numbered by its first use."""
    seen = {}
    return _QUOTED.sub(lambda m: seen.setdefault(m[0], f"`{len(seen)}`"), sql.decode())


def sql_form(sql, form):
    """Whether this is paired form ``form``'s SQL, names aside; two forms may
    have one SQL, as `money * id` over another Decimal."""
    return _form(1, sql_text(sql), _Names(), range(form, form + 1)) == form


def compiled_text(records, names):
    """A bundle's records in order, names and source places aside."""
    lines = []
    for record in records.values():
        kind, values = record.address.kind, list(record.values)
        slots = _COMPILED_NAMES.get(kind, ())
        if kind == "port" and record.get("owner").kind not in {"source", "row"}:
            slots = ()  # a stage port's label is a generated name
        for field, name_kind in slots:
            position = schema.FIELDS[kind].index(field)
            values[position] = names(name_kind, values[position])
        site = records.get(record.get("site")) if kind == "literal" else None
        if site is not None and site.get("role") == "connector":
            values[1] = schema.Scalar("Text", names("L", values[1].value))
        elif kind == "requirement_origin":
            # Its place in the module moves with names and empty lines.
            values[4] = (names("M", record.get("location")[0]),)
        elif kind == "target":
            values[2] = _contract(record.get("contract"), names)
        lines.append(
            json.dumps([kind, schema._wire(tuple(values))], ensure_ascii=False)
        )
    return "\n".join(lines)


def compiled_form(records):
    """The paired form whose bundle these MySQL records are, or None."""
    if rows.AS_MAIN.get() or not any(len(records) == form[3] for form in FORMS):
        return None
    names = _Names()
    try:
        # Loading asks before any check, so even the digest's UTF-8 may fail.
        return _form(2, compiled_text(records, names), names)
    except (ValueError, TypeError, LookupError, AttributeError, RecursionError):
        return None
