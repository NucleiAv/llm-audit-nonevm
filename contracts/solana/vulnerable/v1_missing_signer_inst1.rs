// V1: Missing signer check - Instance 1
// Based on: Jet Protocol upgrade authority audit finding (Neodyme, 2021)
// Vulnerability: The upgrade_authority instruction does not verify that the
// caller is the actual program authority. Any account can invoke this and
// reassign the upgrade authority to an attacker-controlled address.

use anchor_lang::prelude::*;

declare_id!("JET111111111111111111111111111111111111111111");

#[program]
pub mod jet_pool {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, authority: Pubkey) -> Result<()> {
        let pool = &mut ctx.accounts.pool;
        pool.authority = authority;
        pool.bump = *ctx.bumps.get("pool").unwrap();
        Ok(())
    }

    // BUG: no signer check on `new_authority` or verification that
    // ctx.accounts.caller is the current authority. Any account can call this.
    pub fn set_upgrade_authority(
        ctx: Context<SetUpgradeAuthority>,
        new_authority: Pubkey,
    ) -> Result<()> {
        let pool = &mut ctx.accounts.pool;
        pool.authority = new_authority;
        Ok(())
    }

    pub fn deposit(ctx: Context<Deposit>, amount: u64) -> Result<()> {
        let pool = &mut ctx.accounts.pool;
        pool.total_deposits = pool.total_deposits.wrapping_add(amount);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + Pool::SIZE,
        seeds = [b"pool"],
        bump
    )]
    pub pool: Account<'info, Pool>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct SetUpgradeAuthority<'info> {
    #[account(mut, seeds = [b"pool"], bump = pool.bump)]
    pub pool: Account<'info, Pool>,
    // BUG: caller is AccountInfo, not Signer<'info>.
    // No runtime check that this account signed the transaction.
    pub caller: AccountInfo<'info>,
}

#[derive(Accounts)]
pub struct Deposit<'info> {
    #[account(mut, seeds = [b"pool"], bump = pool.bump)]
    pub pool: Account<'info, Pool>,
    pub depositor: Signer<'info>,
}

#[account]
pub struct Pool {
    pub authority: Pubkey,
    pub total_deposits: u64,
    pub bump: u8,
}

impl Pool {
    pub const SIZE: usize = 32 + 8 + 1;
}
